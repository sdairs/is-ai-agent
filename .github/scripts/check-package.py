#!/usr/bin/env python3
"""Build and inspect the actual crate archive before allowing publication."""
import argparse
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = {
    "Cargo.toml", "Cargo.toml.orig", "Cargo.lock", "README.md",
    "LICENSE-MIT", "LICENSE-APACHE", "src/lib.rs",
    "examples/detect.rs", "tests/detect.rs",
}
ALLOWED = REQUIRED | {".cargo_vcs_info.json"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-dirty", action="store_true", help="Allow local uncommitted changes")
    args = parser.parse_args()
    metadata = json.loads(subprocess.check_output(
        ["cargo", "metadata", "--no-deps", "--format-version=1", "--locked", "--offline"], cwd=ROOT))
    package = next(p for p in metadata["packages"] if Path(p["manifest_path"]) == ROOT / "Cargo.toml")
    command = ["cargo", "package", "--locked", "--offline"]
    if args.allow_dirty:
        command.append("--allow-dirty")
    subprocess.run(command, cwd=ROOT, check=True)
    prefix = f"{package['name']}-{package['version']}"
    archive = Path(metadata["target_directory"]) / "package" / (prefix + ".crate")
    with tarfile.open(archive, "r:gz") as crate:
        members = crate.getmembers()
        if any(not m.isfile() or not m.name.startswith(prefix + "/") for m in members):
            raise ValueError("Unexpected archive entry")
        names = {m.name.removeprefix(prefix + "/") for m in members}
    if names - ALLOWED or REQUIRED - names:
        raise ValueError(f"Unexpected package contents: extra={sorted(names - ALLOWED)}, missing={sorted(REQUIRED - names)}")
    print(f"Verified {archive.name}: {len(names)} library distribution files; no harness, inventory or research files.")


if __name__ == "__main__":
    main()
