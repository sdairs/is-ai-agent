#!/usr/bin/env python3
"""Compare two sanitized discovery reports; exit 1 for drift, 2 for invalid evidence."""
import argparse
import json
from pathlib import Path

import run


def observation(report):
    if report.get("stage") != "complete" or not report.get("checks", {}).get("real_shell_tool_executed"):
        raise ValueError("Both reports must contain a verified real tool execution")
    probe = report["probe"]
    # Reports may be from an older library/probe schema. Compare only the known
    # redacted fields; never render arbitrary fields from an input report.
    if probe.get("agent") not in [None, "unknown", *run.HARNESS]:
        raise ValueError("Unknown identity")
    if probe.get("signal") not in [None, "AGENT", "AI_AGENT", *run.MARKERS]:
        raise ValueError("Unknown signal")
    fields = {"agent": probe["agent"], "signal": probe["signal"]}
    if "generic_markers" in probe:
        for name, identity in run.validate_generic(probe["generic_markers"]).items():
            fields[f"generic_markers.{name}"] = identity
    for field, names in [("markers", run.MARKERS), ("exact_markers", run.EXACT_MARKERS),
                         ("session_matches", run.SESSIONS)]:
        for name, value in probe.get(field, {}).items():
            if name not in names or type(value) is not bool:
                raise ValueError("Invalid boolean field")
            fields[f"{field}.{name}"] = value
    discovery = run.validate_discovery(report["discovery"]["agent"], probe["nonce"])
    for name, info in discovery["environment"].items():
        fields[f"environment.{name}"] = info
    # Ancestry, host IDs, times and run nonces are deliberately not drift gates.
    return fields


def compare(before, after):
    if before.get("harness") != after.get("harness") or before.get("platform") != after.get("platform"):
        raise ValueError("Compare the same harness on the same platform")
    old, new = observation(before), observation(after)
    return {key: {"before": old.get(key), "after": new.get(key)}
            for key in sorted(old.keys() | new.keys()) if old.get(key) != new.get(key)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()
    try:
        before, after = (json.loads(path.read_text()) for path in (args.before, args.after))
        changes = compare(before, after)
    except (OSError, ValueError, KeyError, TypeError):
        print("Cannot compare: require two complete, sanitized discovery reports for the same harness/platform.")
        return 2
    print(json.dumps({"drift": bool(changes), "changes": changes}, indent=2))
    return int(bool(changes))


if __name__ == "__main__":
    raise SystemExit(main())
