#!/usr/bin/env python3
"""Build an exact environment inventory from verified watcher artifacts."""
import argparse
import copy
import json
import os
import re
from pathlib import Path

import releases
import run
import watch

DATA = Path("tests/harnesses/inventory/observed.json")
PROVENANCE = ("library_source_sha256", "probe_source_sha256", "adapter_source_sha256")
URL = r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/[0-9]+"
STAGES = {"build_or_run", "gateway", "version", "control", "agent", "artifact", "events", "complete", "missing", "invalid"}
OUTCOMES = {"baseline_failed", "execution_failed", "detection_regression", "new_detection",
            "contract_changed", "new_candidates", "observations_changed", "unchanged"}


def empty():
    return {}


def validate_document(document):
    if not isinstance(document, dict):
        raise ValueError("Invalid harness inventory")
    for name, environment in document.items():
        if name not in run.HARNESS or not isinstance(environment, dict) or len(environment) > 256:
            raise ValueError("Invalid inventory entry")
        for variable, value in environment.items():
            if (not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,95}", variable)
                    or not isinstance(value, str)):
                raise ValueError("Invalid inventory value")
    return document


def validate_runs(runs):
    if not isinstance(runs, dict):
        raise ValueError("Invalid run summary")
    for name, result in runs.items():
        if (name not in run.HARNESS or not isinstance(result, dict)
                or set(result) != {"pinned_version", "candidate_version", "outcome"}
                or result["outcome"] not in OUTCOMES):
            raise ValueError("Invalid run summary fields")
        releases.exact_version(result["pinned_version"])
        releases.exact_version(result["candidate_version"])
    return runs


def verified(report, name):
    if (report.get("harness") != name or report.get("mode") != "mock"
            or report.get("stage") != "complete" or report.get("status") not in {"pass", "fail", "known-gap"}
            or report.get("checks", {}).get("real_shell_tool_executed") is not True):
        raise ValueError("A complete verified mock execution is required")
    releases.exact_version(report["harness_version"])
    if (report["platform"] not in {"linux/amd64", "linux/arm64"}
            or any(not re.fullmatch(r"[0-9a-f]{64}", report[key]) for key in PROVENANCE)):
        raise ValueError("Invalid execution provenance")
    nonce = report["probe"]["nonce"]
    for field in ("probe", "control", "configured_control"):
        run.validate_probe(report[field], nonce)
    for field in ("configured", "agent"):
        run.validate_discovery(report["discovery"][field], nonce)
    if "non_agent_control" in report:
        run.validate_probe(report["non_agent_control"], nonce)
        run.validate_discovery(report["discovery"]["non_agent"], nonce)
    if name == "cline" and "non_agent_control" not in report:
        raise ValueError("Cline requires its non-agent control")
    return report


def observation(report):
    verified(report, report["harness"])
    discovery = report["discovery"]["agent"]
    if discovery["schema"] != 3:
        raise ValueError("Fresh discovery with exact values is required")
    environment = {name: info["value"] for name, info in discovery["environment"].items()
                   if info["change"] != "removed"}
    validate_document({report["harness"]: environment})
    return environment


def difference(before, after):
    changes = {}
    for name in sorted(before.keys() | after.keys()):
        old, new = before.get(name, {}), after.get(name, {})
        if old != new or (name in before) != (name in after):
            changes[name] = {
                "added": {key: new[key] for key in sorted(new.keys() - old.keys())},
                "removed": {key: old[key] for key in sorted(old.keys() - new.keys())},
                "changed": {key: {"before": old[key], "after": new[key]}
                            for key in sorted(old.keys() & new.keys()) if old[key] != new[key]},
            }
    return changes


def collect(previous, artifacts, names, run_url):
    validate_document(previous)
    if not re.fullmatch(URL, run_url):
        raise ValueError("Expected a GitHub Actions evidence URL")
    result, errors, runs = copy.deepcopy(previous), {}, {}
    for name in names:
        # The artifact's name scopes it; a claimed harness ID alone is insufficient.
        run_id = run_url.rsplit("/", 1)[-1]
        folders = [(int(match[1]), folder) for folder in artifacts.glob(f"watch-{name}-{run_id}-*")
                   if (match := re.fullmatch(rf"watch-{re.escape(name)}-{run_id}-(\d+)", folder.name))]
        # A rerun may retain artifacts from earlier attempts of successful jobs.
        latest = max((attempt for attempt, _ in folders), default=0)
        paths = [path for attempt, folder in folders if attempt == latest for path in folder.glob("*/comparison.json")]
        if len(paths) != 1:
            errors[name] = {"stage": "missing", "reason": "missing_or_duplicate_artifact"}
            continue
        parent = paths[0].parent
        candidate_version = None
        try:
            if (parent / "resolved.json").is_file():
                resolved = json.loads((parent / "resolved.json").read_text())
                candidate_version = releases.exact_version(resolved["version"])
            before = json.loads((parent / "baseline.json").read_text())
            after = json.loads((parent / "candidate.json").read_text())
            # Candidate collection is independent of the old pinned release.
            # A failed baseline prevents comparison, not a verified new snapshot.
            if after.get("stage") != "complete" or after.get("checks", {}).get("real_shell_tool_executed") is not True:
                stage = after.get("stage")
                errors[name] = {"stage": stage if stage in STAGES else "invalid", "reason": "unverified_execution", "version": candidate_version}
                continue
            verified(after, name)
            if after["harness_version"] != candidate_version:
                raise ValueError("Resolved version differs from execution")
            entry = observation(after)
            if before.get("stage") == "complete" and before.get("checks", {}).get("real_shell_tool_executed") is True:
                verified(before, name)
                if (before["platform"] != after["platform"] or before["probe"]["nonce"] == after["probe"]["nonce"]
                        or any(before[k] != after[k] for k in PROVENANCE)):
                    raise ValueError("Comparison must use fresh probes on the same measurement code/platform")
                outcome = watch.assess(before, after)["outcome"]
            else:
                outcome = "baseline_failed"
            runs[name] = {"pinned_version": before.get("harness_version", run.HARNESS[name]["version"]),
                          "candidate_version": after["harness_version"], "outcome": outcome}
            result[name] = entry
        except (OSError, ValueError, KeyError, TypeError):
            errors[name] = {"stage": "invalid", "reason": "invalid_or_incomplete_evidence", "version": candidate_version}
    return result, errors, validate_runs(runs)


def render(document):
    validate_document(document)
    lines = ["# Observed harness environments", "",
             "Variables present in each harness's Linux command environment, including inherited configuration. "
             "Values are captured exactly from isolated mock runs, including dummy API keys and generated session IDs. "
             "The table uses JSON string notation to preserve whitespace and empty strings.", "",
             "Generated from verified probes. Test results and execution details live in the CI artifacts; "
             "the detector does not read this inventory."]
    for name, environment in sorted(document.items()):
        lines += ["", f"## {name}", "", "| Variable | Value |", "| --- | --- |"]
        for variable, value in sorted(environment.items()):
            lines.append(f"| `{variable}` | {run.markdown_value(value)} |")
    return "\n".join(lines) + "\n"


def report_markdown(changes, errors, run_url, runs):
    lines = ["# Harness observation changes", "", f"[Weekly evidence]({run_url})", "",
             "These are observations, not a diagnosis of an upstream defect. A new generic marker or a removed "
             "legacy marker can be a compatible migration. Detector rules remain separately reviewed.", ""]
    for name, change in changes.items():
        lines += [f"## {name}: inventory delta", "",
                  "| Variable | Before | After |", "| --- | --- | --- |"]
        for key, value in change["added"].items():
            lines.append(f"| `{key}` | absent | {run.markdown_value(value)} |")
        for key, value in change["removed"].items():
            lines.append(f"| `{key}` | {run.markdown_value(value)} | absent |")
        for key, values in change["changed"].items():
            lines.append(f"| `{key}` | {run.markdown_value(values['before'])} | {run.markdown_value(values['after'])} |")
        lines.append("")
    for name, result in sorted(runs.items()):
        if name in changes or result["outcome"] != "unchanged":
            lines += [f"{name}: pinned `{result['pinned_version']}` → candidate `{result['candidate_version']}`; "
                      f"comparison: `{result['outcome']}`. See the linked run for detection results and controls.", ""]
    for name, error in sorted(errors.items()):
        lines += [f"## {name}: probe unavailable", "", f"Candidate: `{error.get('version') or 'unresolved'}`; "
                  f"stage: `{error['stage']}`; reason: `{error['reason']}`. "
                  "Previous inventory retained; no missing-marker conclusion.", ""]
    if not changes and not errors and all(r["outcome"] == "unchanged" for r in runs.values()):
        lines += ["No inventory or test changes. No inventory update is needed.", ""]
    else:
        lines += ["Review the changed variables and controls, reproduce with the recorded version, then check upstream "
                  "documentation/source. Changes to our collector can also change the inventory; "
                  "do not attribute every delta to upstream.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--previous", type=Path, default=run.ROOT / DATA)
    parser.add_argument("--output", type=Path, default=run.ROOT / "target/harness-inventory")
    parser.add_argument("--harness", choices=["all", *run.HARNESS], default="all")
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()
    previous = json.loads(args.previous.read_text()) if args.previous.exists() else empty()
    names = list(run.HARNESS) if args.harness == "all" else [args.harness]
    current, errors, runs = collect(previous, args.artifacts, names, args.run_url)
    changes = difference(previous, current)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "observed.json").write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
    (args.output / "README.md").write_text(render(current))
    (args.output / "delta.json").write_text(json.dumps({"changes": changes, "errors": errors, "runs": runs}, indent=2, sort_keys=True) + "\n")
    markdown = report_markdown(changes, errors, args.run_url, runs)
    (args.output / "summary.md").write_text(markdown)
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(path, "a") as output:
            output.write(markdown)
    print(f"Inventory: {len(current)} entries; {len(changes)} changes; {len(errors)} unavailable probes.")
    # A failed probe must not prevent the publisher from retaining old data and
    # reporting the failure. Per-harness watcher jobs retain their failure status.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
