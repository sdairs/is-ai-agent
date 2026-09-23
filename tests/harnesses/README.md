# Harness environment inventory

This lab runs sixteen unmodified agent CLIs inside Docker and records the exact
environment visible to their real shell tools. A scripted local provider requests
the probe command: no model, vendor account or real inference credential is needed.
Use the resulting inventory to research identification signals; detector changes
belong in separate PRs.

The [structured inventory](inventory/observed.json) is **harness → variable → value**.
It includes inherited settings, empty strings, dummy API keys, paths and generated
session IDs. Values are not redacted or normalized. The Markdown reference sheet
is generated as a CI artifact instead of duplicating the JSON in the repository.

## Run locally

Start Docker or OrbStack and use Python 3.10+:

```sh
python3 tests/harnesses/run.py --harness pi --discover
python3 tests/harnesses/run.py --harness cline --discover
python3 tests/harnesses/watch.py --harness goose
python3 tests/harnesses/watch.py --harness qwen-code --candidate 0.24.3
```

[The manifest](harnesses.json) lists harness IDs, pinned releases, real tools and
installation metadata. It contains no expected detector rules. npm adapters can
trial another exact version with `run.py --version`. Goose/VTCode assets, Hermes
source archives and Junie's separate binary version require matching metadata;
use the release resolver in `watch.py` or update the manifest for those adapters.

The first build downloads public images and packages. Later builds reuse Docker's
cache; `--skip-build` requires a matching source fingerprint. Nothing installs on
the host. Hermes uses an immutable source archive, and binary archives are
checksum-verified. Transitive installer dependencies are not completely locked.

## What a successful collection means

The CLI must execute the exact probe command, return the same fresh output and
nonce through its real tool, and exit successfully. The gateway never executes
the command. CLI events establish the roundtrip for Pi, Qwen Code and OpenCode;
the other adapters use the provider's observed tool result. The gateway supports
Chat Completions, Responses, Anthropic Messages and Gemini protocols. Junie also
uses its advertised `submit` tool to finish.

Discovery collects these controls alongside the agent environment:

- A clean shell runs the unchanged library's detection probe.
- The configured launcher environment is captured before starting the agent.
- The real agent shell runs the same probe plus exact environment discovery.
- Cline also runs `skill list` without an agent turn; an argument-checking probe
  replaces its `npx skills@latest list` dependency.

Detection and control results are observations, not collection pass criteria.
An unknown identity, a missing session rule or a fork detected as its parent does
not discard successfully captured variables. This PR does not change library
rules. See [the research notes](discovery.md) for candidate signals and controls.

The lab-only Rust probe lives at `tests/harnesses/probe.rs`; the Docker build
registers it as an example only in its disposable build context. It is not a
published crate target. The crate's explicit package include list excludes the
entire lab. CI and the release workflow build and inspect the actual archive
with `.github/scripts/check-package.py` before publication.

## Automated collection

[Harness environment collection](../../.github/workflows/harness-tests.yml) runs
pinned releases on PRs, pushes to `main` and manual dispatch. Each harness has its
own job. Rust/library tests and collector tests run separately. The lab is not a
crate-release gate; the release workflow checks the package contents directly.

[Upstream harness changes](../../.github/workflows/harness-watch.yml) runs Saturdays
at 08:17 UTC and on manual dispatch. It resolves `latest` once, records the exact
installation metadata, and runs fresh pinned and candidate releases on the same
platform with the same measurement code. npm `latest` follows the publisher's
tag; GitHub releases use the latest stable release. The GitHub metadata token
stays on the host and never enters the build or agent containers.

Environment and detection differences are research output and do not fail the
watcher. Resolution and execution failures do. Generated IDs and container names
can change on every run; those exact changes remain available in the reports.
A verified candidate updates the inventory even if the older pin cannot run.
A failed candidate retains the previous inventory entry and is reported as
unavailable, never as evidence that its variables disappeared.

Scheduled and manual `all` / `latest` runs on the default branch propose an
inventory-only PR on `codex/harness-inventory`. The publisher may update only
`inventory/observed.json`; it cannot update the library, manifest or default
branch, force-push, or merge. It rejects stale results and unrelated branch
changes. PR runs and single-harness trials produce artifact previews only.
There are no automatic investigation issues: the inventory PR is the review queue.
GitHub Actions must be allowed to create PRs in the repository settings.

Pinned-run evidence is retained for 14 days; weekly evidence for 90 days. Reports
record versions, platform, image/source fingerprints, controls, detection and
exact environment values. Git history preserves merged inventory snapshots.
The inventory is one observed Linux headless command surface per harness, not
complete coverage of IDEs, PTYs, SDKs, nested agents or resumed sessions.

## Inspect and regenerate

```sh
python3 tests/harnesses/compare.py /path/to/before/report.json /path/to/after/report.json
python3 tests/harnesses/inventory.py --artifacts /path/to/downloaded/artifacts \
  --run-url https://github.com/OWNER/REPO/actions/runs/RUN_ID
```

The runner writes validated evidence under `target/harness-runs/`. The watcher
writes both reports and a comparison under `target/harness-watch/`. Aggregation
writes JSON, a Markdown reference sheet and a delta report to
`target/harness-inventory/`. These local artifacts are ignored by Git. The manual
comparison exits 0 for unchanged, 1 for drift, and 2 for invalid evidence.

Variable names must match `[A-Za-z_][A-Za-z0-9_]{0,95}`. Invalid or longer names
are omitted; more than 256 variables fails validation rather than truncating.
Raw transcripts, CLI homes and provider request bodies are not retained.
Containers have no host configuration, credentials, source tree or Docker socket;
only disposable evidence directories are mounted. Runtime networking is internal
and there is no live-inference mode.

## Maintain the lab

Add installation metadata to `harnesses.json` and launcher configuration to
`entrypoint.mjs`. New provider protocols may need a gateway adapter. Test the real
command roundtrip before treating a variable as evidence; review upstream source
and appropriate non-agent controls before proposing a detector rule separately.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/harnesses -p 'test_*.py'
cargo test --locked
cargo fmt --check
cargo clippy --lib -- -D warnings
rustfmt --edition 2024 --check tests/harnesses/probe.rs
python3 .github/scripts/check-package.py --allow-dirty
```

The final command builds and verifies the actual publishable archive locally.
CI and release checks omit `--allow-dirty`.
