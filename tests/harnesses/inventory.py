#!/usr/bin/env python3
"""Build a redacted, descriptive inventory from verified watcher artifacts."""
import argparse
import copy
import json
import os
import re
from pathlib import Path

import releases
import run

DATA = Path("tests/harnesses/inventory/observed.json")
DOCUMENT = Path("tests/harnesses/inventory/README.md")
DETECTION = ("agent", "signal", "session_present", "markers", "exact_markers", "session_matches", "generic_markers")
PROVENANCE = ("library_source_sha256", "probe_source_sha256", "adapter_source_sha256")
URL = r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/[0-9]+"
STAGES = {"build_or_run", "gateway", "version", "control", "agent", "artifact", "events", "complete", "missing", "invalid"}
EXACT = {"DSH_SHELL": "1", "KILO": "1", "OPENCLAW_SHELL": "exec", "HERMES_AGENT": "true", "VTCODE": "1"}


def empty():
    return {"schema": 1, "harnesses": {}}


def validate_environment(environment):
    return run.validate_discovery({"schema": 1, "nonce": "inventory", "ancestry": ["other"],
                                   "environment": environment}, "inventory")["environment"]


def validate_document(document):
    if not isinstance(document, dict) or set(document) != {"schema", "harnesses"} or document["schema"] != 1:
        raise ValueError("Invalid inventory schema")
    if not isinstance(document["harnesses"], dict):
        raise ValueError("Invalid harness inventory")
    for name, entry in document["harnesses"].items():
        if name not in run.HARNESS or set(entry) != {"version", "platform", "tool", "detection", "environment",
                "non_agent_environment", "controls", "contract_status", "evidence"}:
            raise ValueError("Invalid inventory entry")
        releases.exact_version(entry["version"])
        if entry["platform"] not in {"linux/amd64", "linux/arm64"} or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,95}", entry["tool"]):
            raise ValueError("Invalid execution surface")
        if entry["contract_status"] not in {"pass", "fail", "known-gap"}:
            raise ValueError("Invalid contract status")
        detection = entry["detection"]
        if set(detection) != set(DETECTION):
            raise ValueError("Invalid detection inventory")
        run.validate_probe({**detection, "schema": 4, "nonce": "inventory", "library_version": run.library_version()}, "inventory")
        validate_environment(entry["environment"])
        if entry["non_agent_environment"] is not None:
            validate_environment(entry["non_agent_environment"])
        controls = entry["controls"]
        if (set(controls) != {"plain", "configured", "non_agent"}
                or type(controls["plain"]) is not bool or type(controls["configured"]) is not bool
                or (controls["non_agent"] is not None and type(controls["non_agent"]) is not bool)):
            raise ValueError("Invalid control inventory")
        evidence = entry["evidence"]
        if set(evidence) != {"run_url", "observed_at", "probe_schema", *PROVENANCE}:
            raise ValueError("Invalid evidence provenance")
        if not re.fullmatch(URL, evidence["run_url"]) or evidence["probe_schema"] != 4:
            raise ValueError("Invalid evidence link/schema")
        if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?\+00:00", evidence["observed_at"]):
            raise ValueError("Invalid observation date")
        if any(not re.fullmatch(r"[0-9a-f]{64}", evidence[key]) for key in PROVENANCE):
            raise ValueError("Invalid source fingerprint")
    return document


def verified(report, name):
    if (report.get("harness") != name or report.get("mode") != "mock"
            or report.get("stage") != "complete" or report.get("status") not in {"pass", "fail", "known-gap"}
            or report.get("checks", {}).get("real_shell_tool_executed") is not True):
        raise ValueError("A complete verified mock execution is required")
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


def observation(report, run_url):
    name = report["harness"]
    verified(report, name)
    record = {
        "version": report["harness_version"], "platform": report["platform"], "tool": run.HARNESS[name]["tool"],
        "detection": {key: report["probe"][key] for key in DETECTION},
        "environment": report["discovery"]["agent"]["environment"],
        "non_agent_environment": report["discovery"].get("non_agent", {}).get("environment"),
        "controls": {"plain": report["control"]["agent"] is None,
                     "configured": report["configured_control"]["agent"] is None,
                     "non_agent": report["non_agent_control"]["agent"] is None if "non_agent_control" in report else None},
        "contract_status": report["status"],
        "evidence": {"run_url": run_url, "observed_at": report["timestamp"], "probe_schema": report["probe"]["schema"],
                     **{key: report[key] for key in PROVENANCE}},
    }
    validate_document({"schema": 1, "harnesses": {name: record}})
    return record


def substantive(entry):
    # Dates/run URLs alone must not create weekly commits or repeat alerts.
    return {**{k: v for k, v in entry.items() if k != "evidence"},
            "measurement": {k: entry["evidence"][k] for k in (*PROVENANCE, "probe_schema")}}


def delta(before, after):
    if before is None:
        return {"kind": "first_observation", "from_version": None, "to_version": after["version"]}
    if substantive(before) == substantive(after):
        return None
    changes = {}
    for field in ("platform", "tool"):
        if before[field] != after[field]:
            changes[field] = {"before": before[field], "after": after[field]}
    for field in ("detection", "environment", "non_agent_environment", "controls"):
        old, new = before[field] or {}, after[field] or {}
        for key in sorted(old.keys() | new.keys()):
            if old.get(key) != new.get(key):
                if field == "detection" and isinstance(old.get(key), dict) and isinstance(new.get(key), dict):
                    for subkey in sorted(old[key].keys() | new[key].keys()):
                        if old[key].get(subkey) != new[key].get(subkey):
                            changes[f"{field}.{key}.{subkey}"] = {"before": old[key].get(subkey), "after": new[key].get(subkey)}
                else:
                    changes[f"{field}.{key}"] = {"before": old.get(key), "after": new.get(key)}
    measurement = (before["platform"] != after["platform"] or
                   any(before["evidence"][k] != after["evidence"][k] for k in (*PROVENANCE, "probe_schema")))
    old_id, new_id = before["detection"]["agent"], after["detection"]["agent"]
    if not changes:
        kind = "version_or_measurement_only"
    elif measurement:
        kind = "measurement_changed_review_required"
    elif before["controls"] != after["controls"]:
        kind = "control_behavior_changed"
    elif old_id != new_id:
        kind = "new_detection" if old_id is None else "detection_changed"
    else:
        kind = "signals_changed_detection_preserved" if old_id is not None else "signals_changed_still_undetected"
    return {"kind": kind, "from_version": before["version"], "to_version": after["version"],
            "measurement_changed": measurement, "changes": changes}


def difference(before, after):
    return {name: change for name, entry in sorted(after["harnesses"].items())
            if (change := delta(before["harnesses"].get(name), entry)) is not None}


def collect(previous, artifacts, names, run_url):
    validate_document(previous)
    if not re.fullmatch(URL, run_url):
        raise ValueError("Expected a GitHub Actions evidence URL")
    result, errors = copy.deepcopy(previous), {}
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
            for report in (before, after):
                if report.get("stage") != "complete" or report.get("checks", {}).get("real_shell_tool_executed") is not True:
                    stage = report.get("stage")
                    errors[name] = {"stage": stage if stage in STAGES else "invalid", "reason": "unverified_execution", "version": candidate_version}
                    break
                verified(report, name)
            else:
                if (before["platform"] != after["platform"] or before["probe"]["nonce"] == after["probe"]["nonce"]
                        or any(before[k] != after[k] for k in PROVENANCE)):
                    raise ValueError("Comparison must use fresh probes on the same measurement code/platform")
                if after["harness_version"] != candidate_version:
                    raise ValueError("Resolved version differs from execution")
                entry = observation(after, run_url)
                old = previous["harnesses"].get(name)
                if old is None or substantive(old) != substantive(entry):
                    result["harnesses"][name] = entry
        except (OSError, ValueError, KeyError, TypeError):
            errors[name] = {"stage": "invalid", "reason": "invalid_or_incomplete_evidence", "version": candidate_version}
    return result, errors


def render(document):
    validate_document(document)
    lines = ["# Observed harness environments", "", "Generated by `inventory.py`; descriptive evidence only. The detector and its test expectations do not read these files.", "",
             "This records the Linux noninteractive shell-tool surface. Values, tokens, session IDs and paths are redacted. Every portable variable name is listed (maximum 96 characters); inherited configuration is not an agent identity. Missing non-agent controls are untested, not evidence of absence.", "",
             "`added` / `changed` / `removed` / `unchanged` compare the command environment with its configured launch baseline. Generic identities are independently classified by the library, not literal raw values. An unchanged snapshot keeps its original evidence link; every weekly run still retains fresh artifacts.", "",
             "| Harness | Version | Detected as | Selected signal |", "| --- | --- | --- | --- |"]
    for name, e in sorted(document["harnesses"].items()):
        lines.append(f"| [{name}](#{name}) | {e['version']} | {e['detection']['agent'] or 'undetected'} | {e['detection']['signal'] or 'none'} |")
    for name, e in sorted(document["harnesses"].items()):
        d = e["detection"]
        lines += ["", f"## {name}", "", f"Version `{e['version']}` · `{e['platform']}` · tool `{e['tool']}` · contract `{e['contract_status']}`.", "",
                  f"[Recorded execution]({e['evidence']['run_url']}) at {e['evidence']['observed_at']}.", "",
                  f"Generic classifications: `AGENT` → `{d['generic_markers']['AGENT'] or 'absent/blank'}`; `AI_AGENT` → `{d['generic_markers']['AI_AGENT'] or 'absent/blank'}`.", "",
                  "Controls (no detection expected): " + "; ".join(f"{key}: {'untested' if e['controls'][key] is None else 'clear' if e['controls'][key] else 'detected'}" for key in ("plain", "configured", "non_agent")) + ".", "",
                  "| Variable | Change from launch baseline | Nonblank in tool | Non-agent child | Probe observation |",
                  "| --- | --- | --- | --- | --- |"]
        for variable, info in sorted(e["environment"].items()):
            negative = e["non_agent_environment"]
            control = "untested" if negative is None else "present" if negative.get(variable, {}).get("nonblank") else "absent/blank"
            roles = []
            if variable == d["signal"]:
                roles.append("selected detection signal")
            if d["markers"].get(variable):
                roles.append("marker present")
            if variable in d["exact_markers"]:
                roles.append(f'equals `"{EXACT[variable]}"`: ' + str(d["exact_markers"][variable]).lower())
            if variable in d["generic_markers"]:
                roles.append("generic identity: " + (d["generic_markers"][variable] or "none"))
            if d["session_matches"].get(variable):
                roles.append("matches detected session")
            lines.append(f"| `{variable}` | {info['change']} | {str(info['nonblank']).lower()} | {control} | {'; '.join(roles) or 'discovery observation'} |")
    return "\n".join(lines) + "\n"


def report_markdown(changes, errors, run_url):
    lines = ["# Harness observation changes", "", f"[Weekly evidence]({run_url})", "",
             "These are observations, not a diagnosis of an upstream defect. A new generic marker or a removed legacy marker can be a compatible migration. Detector rules and test expectations remain separately reviewed.", ""]
    meaningful = {name: change for name, change in changes.items() if change["kind"] != "version_or_measurement_only"}
    for name, change in changes.items():
        lines += [f"## {name}: {change['kind']}", "", f"Version `{change['from_version']}` → `{change['to_version']}`.", ""]
        if change.get("measurement_changed"):
            lines += ["The library, probe, adapter, or platform also changed; do not attribute this delta solely to the CLI release.", ""]
        if change.get("changes"):
            lines += ["| Observation | Before | After |", "| --- | --- | --- |"]
            for key, values in change["changes"].items():
                lines.append(f"| `{key}` | `{json.dumps(values['before'], sort_keys=True)}` | `{json.dumps(values['after'], sort_keys=True)}` |")
            lines.append("")
    for name, error in errors.items():
        lines += [f"## {name}: probe unavailable", "", f"Candidate: `{error.get('version') or 'unresolved'}`; stage: `{error['stage']}`; reason: `{error['reason']}`. Previous inventory retained; no missing-marker conclusion.", ""]
    if not changes and not errors:
        lines += ["No inventory changes. No commit or issue is needed.", ""]
    if meaningful or errors:
        lines += ["Review the changed variables and controls, reproduce with the recorded version, then check upstream documentation/source. Decide separately whether to update our rule, extend compatibility, or report an upstream problem.", ""]
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
    current, errors = collect(previous, args.artifacts, names, args.run_url)
    changes = difference(previous, current)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "observed.json").write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
    (args.output / "README.md").write_text(render(current))
    (args.output / "delta.json").write_text(json.dumps({"changes": changes, "errors": errors}, indent=2, sort_keys=True) + "\n")
    markdown = report_markdown(changes, errors, args.run_url)
    (args.output / "summary.md").write_text(markdown)
    if path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(path, "a") as output:
            output.write(markdown)
    print(f"Inventory: {len(current['harnesses'])} entries; {len(changes)} changes; {len(errors)} unavailable probes.")
    # A failed probe must not prevent the publisher from retaining old data and
    # reporting the failure. Per-harness watcher jobs retain their failure status.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
