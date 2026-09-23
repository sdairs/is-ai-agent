#!/usr/bin/env python3
"""Compare a reviewed pinned CLI with a freshly resolved public release."""
import argparse
import contextlib
import io
import json
import os
import subprocess
import uuid
from pathlib import Path
from types import SimpleNamespace

import compare
import releases
import run


def assess(before, after):
    """A completed command is mandatory before interpreting detection changes."""
    if before.get("status") not in ("pass", "known-gap"):
        return {"outcome": "baseline_failed", "changes": {}, "candidates": []}
    if not after.get("checks", {}).get("real_shell_tool_executed"):
        return {"outcome": "execution_failed", "changes": {}, "candidates": []}
    changes = compare.compare(before, after)
    old_agent, new_agent = before["probe"]["agent"], after["probe"]["agent"]
    negative = after.get("discovery", {}).get("non_agent", {}).get("environment", {})
    candidates = []
    for field, delta in changes.items():
        if field.startswith("environment."):
            name = field.removeprefix("environment.")
            observed = delta["after"] or {}
            if (observed.get("change") == "added" and observed.get("nonblank")
                    and not negative.get(name, {}).get("nonblank")):
                candidates.append(name)
    if old_agent is not None and old_agent != new_agent:
        outcome = "detection_regression"
    elif old_agent is None and new_agent is not None:
        outcome = "new_detection"
    elif after.get("status") not in ("pass", "known-gap"):
        outcome = "contract_changed"
    elif candidates:
        outcome = "new_candidates"
    elif changes:
        outcome = "observations_changed"
    else:
        outcome = "unchanged"
    return {"outcome": outcome, "changes": changes, "candidates": candidates}


def execute(harness, spec):
    original = run.HARNESS[harness]
    output = run.ROOT / "target/harness-runs" / harness
    previous = set(output.glob("*/report.json"))
    try:
        run.HARNESS[harness] = spec
        # run.py emits schema-validated reports; keep console output concise.
        # Public build progress is still emitted by the build subprocess.
        with contextlib.redirect_stdout(io.StringIO()):
            run.run(SimpleNamespace(harness=harness, mode="mock", discover=True,
                    expect_undetected=bool(spec.get("known_gap")), skip_build=False,
                    base_url=None, model=None, token_file=None))
        created = set(output.glob("*/report.json")) - previous
        if len(created) != 1:
            raise ValueError("Expected one fresh report")
        path = created.pop()
        return json.loads(path.read_text())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        return {"status": "error", "error_type": type(error).__name__, "stage": "build_or_run"}
    finally:
        run.HARNESS[harness] = original


def summary(result):
    # All rendered fields are controlled identifiers or validated versions.
    lines = [f"### {result['harness']}: {result['outcome']}", "",
             f"Pinned: `{result['pinned_version']}`. Candidate: `{result.get('candidate_version', 'unresolved')}`.", "",
             "| Observation | Before | After |", "| --- | --- | --- |"]
    for field, delta in result.get("changes", {}).items():
        lines.append(f"| `{field}` | `{json.dumps(delta['before'], sort_keys=True)}` | `{json.dumps(delta['after'], sort_keys=True)}` |")
    if not result.get("changes"):
        lines.append("| Delta | No interpreted delta | See outcome and evidence |")
    if result.get("candidates"):
        lines += ["", "New candidate names need source/negative-control review; presence is not a confirmed heuristic."]
    for name, report in result.get("runs", {}).items():
        lines += ["", f"{name.capitalize()} run: `{report['status']}` at `{report['stage']}`."]
    if result.get("error_type"):
        lines += ["", f"Resolution/evidence error: `{result['error_type']}` (details omitted from artifacts)."]
    lines += ["", "An execution failure is not evidence that a marker disappeared. Raw environment values are never retained.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", choices=list(run.HARNESS), required=True)
    parser.add_argument("--candidate", default="latest", help="latest, or an exact public release (Hermes: latest only)")
    args = parser.parse_args()
    pinned = run.HARNESS[args.harness]
    destination = run.ROOT / "target/harness-watch" / args.harness / uuid.uuid4().hex
    destination.mkdir(parents=True)
    result = {"schema": 1, "harness": args.harness, "pinned_version": pinned["version"]}
    try:
        candidate = releases.resolve(args.harness, pinned, args.candidate)
        result["candidate_version"] = candidate["version"]
        (destination / "resolved.json").write_text(json.dumps(candidate, indent=2) + "\n")
        before = execute(args.harness, pinned)
        after = execute(args.harness, candidate)
        result["runs"] = {name: {"status": report["status"], "stage": report["stage"]}
                          for name, report in [("baseline", before), ("candidate", after)]}
        for name, report in [("baseline", before), ("candidate", after)]:
            (destination / f"{name}.json").write_text(json.dumps(report, indent=2) + "\n")
        result.update(assess(before, after))
    except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration, subprocess.SubprocessError) as error:
        result.update(outcome="resolution_or_evidence_error", error_type=type(error).__name__, changes={}, candidates=[])
    (destination / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    markdown = summary(result)
    (destination / "summary.md").write_text(markdown)
    if step_summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(step_summary, "a") as target:
            target.write(markdown)
    print(markdown)
    print("Evidence: " + str(destination))
    return 0 if result["outcome"] == "unchanged" else 1


if __name__ == "__main__":
    raise SystemExit(main())
