#!/usr/bin/env python3
"""Replay captured environments through detect_with, without launching harnesses."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "tests/harnesses/inventory/observed.json"

# NUL framing preserves whitespace, newlines and empty values without adding a
# JSON dependency to the Rust crate. These are lookups, never process env writes.
DRIVER = r'''
use is_ai_agent::{detect_with, Signal};
use std::{collections::HashMap, io::{self, Read, Write}};

fn main() {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).unwrap();
    let fields: Vec<_> = input.split_terminator('\0').collect();
    assert_eq!(fields.len() % 2, 0);
    let env: HashMap<_, _> = fields.chunks_exact(2)
        .map(|pair| (pair[0], pair[1])).collect();
    let result = detect_with(|key| env.get(key).map(|value| (*value).into()), |_| false);
    let mut output = io::stdout().lock();
    if let Some(agent) = result {
        let signal = match agent.signal {
            Signal::EnvVar { name, .. } => name,
            _ => panic!("filesystem lookup is disabled"),
        };
        write!(output, "{}\0{}\0{}\0{}", agent.id.as_str(), signal,
            agent.session_id.is_some(), agent.session_id.as_deref().unwrap_or("")).unwrap();
    } else {
        write!(output, "\0\0false\0").unwrap();
    }
}
'''


def replay(inventory, source):
    with tempfile.TemporaryDirectory(prefix="is-ai-agent-audit-") as temp:
        build = Path(temp)
        library = build / "libis_ai_agent.rlib"
        (build / "lib.rs").write_text(source)
        (build / "audit.rs").write_text(DRIVER)
        subprocess.run([
            "rustc", "--edition=2024", "--crate-name=is_ai_agent", "--crate-type=rlib",
            str(build / "lib.rs"), "-o", str(library),
        ], check=True)
        subprocess.run([
            "rustc", "--edition=2024", str(build / "audit.rs"),
            "--extern", f"is_ai_agent={library}", "-o", str(build / "audit"),
        ], check=True)
        results = {}
        for harness, environment in sorted(inventory.items()):
            fields = [field for pair in environment.items() for field in pair]
            if any(not isinstance(field, str) or "\0" in field for field in fields):
                raise ValueError(f"{harness}: environment must contain NUL-free strings")
            raw = subprocess.check_output(
                [str(build / "audit")], input="".join(field + "\0" for field in fields).encode(),
            ).decode()
            identity, signal, present, session = raw.split("\0", 3)
            results[harness] = {
                "agent": identity or None,
                "signal": signal or None,
                "session_present": present == "true",
                # Equality is an observation, not proof of which key supplied it.
                # Codex root and thread IDs can have equal captured values.
                "session_matches": sorted(key for key, value in environment.items()
                                          if present == "true" and value == session),
            }
        return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=INVENTORY)
    parser.add_argument("--revision", help="Read src/lib.rs from a local Git revision")
    args = parser.parse_args()
    source = (subprocess.check_output(
        ["git", "show", f"{args.revision}:src/lib.rs"], cwd=ROOT,
    ).decode() if args.revision else (ROOT / "src/lib.rs").read_text())
    inventory = json.loads(args.inventory.read_text())
    print(json.dumps(replay(inventory, source), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
