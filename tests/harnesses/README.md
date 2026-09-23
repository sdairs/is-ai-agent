# Real harness integration tests

These tests install **unmodified, pinned CLI releases inside Docker**, point
those CLIs at a local scripted model provider, and ask their real shell tools to
run a Rust probe linked against this repository. No LLM, vendor account or real
credential is needed. The same runner works with OrbStack locally and Docker on
GitHub-hosted Linux runners.

| Harness | Pinned version | Real tool | Session contract |
| --- | --- | --- | --- |
| Pi | 0.87.1 | `bash` | `PI_SESSION_ID` |
| Qwen Code | 0.24.4 | `run_shell_command` | `QWEN_CODE_SESSION_ID` |
| OpenCode | 1.18.32 | `bash` | No ordinary-shell session ID asserted |

Versions, package names and expected signals live in
[harnesses.json](harnesses.json). This is coverage of the specified Linux
noninteractive CLI surface, not every version, OS, IDE, SDK, hook, MCP server,
persistent terminal, resume/reset path or human-command feature.

## Run locally

Start OrbStack (or Docker) and use Python 3.10+:

```sh
python3 tests/harnesses/run.py --harness pi
python3 tests/harnesses/run.py --harness qwen-code
python3 tests/harnesses/run.py --harness opencode
```

The first build downloads public images and the published npm package. Subsequent
builds reuse Docker's cache. `--skip-build` reuses an existing image only when its
build-input fingerprint still matches. No harness is installed on the host.

## What is actually tested

```text
Host runner
  ├─ plain Bash control → compiled Rust probe → no agent expected
  └─ real CLI → real shell tool → same compiled probe → JSON file
         │
         └─ private Docker network → scripted provider
```

The fake provider returns a standard OpenAI-compatible tool-call response.
It chooses the shell tool from the CLI's advertised tools and requests exactly
one probe command. The CLI performs the command execution itself. The provider
returns a final text response after receiving the tool result.

A successful run requires all of the following:

1. The plain-shell control detects no agent.
2. The CLI executes the exact command once, emits a successful tool result, and
   finishes successfully with exit code zero.
3. The tool output matches the freshly written probe artifact and run nonce.
4. The library identifies the expected harness using its actual markers.
5. The harness supplies the expected markers/session context, and the library
   returns the matching session ID (or none for OpenCode).

The runner does not set identity or session markers. A clean container prevents
ambient Codex/CI environment variables from contaminating attribution. A model
saying “done”, an unrelated tool result, stale file, wrong command, or nonzero
exit cannot pass. This is regression evidence for cooperative software, not
cryptographic attestation against an agent deliberately forging artifacts.

The Pi test initially exposed missing session extraction in `is-ai-agent` 0.5.0;
this change adds its nonblank session fallback/extraction and focused unit tests.
The [historical report](evidence/pi-0.87.1-mock.json) records the original failure.
New runs test the fixed implementation.

## GitHub Actions

[Harness integration tests](../../.github/workflows/harness-tests.yml) runs on
pull requests, pushes to `main`, and manual dispatch. A separate matrix job runs
each harness; one failure does not cancel the others. It also runs Rust tests,
formatting, Clippy, documentation generation, and the Python verifier/gateway tests.

[The release workflow](../../.github/workflows/release.yml) calls the same
reusable workflow and requires it to pass **before publishing to crates.io**.
No inference secrets are passed to these jobs. Checkout does not persist GitHub
credentials. The publishing token is still confined to the publish step.

Each matrix job uploads only schema-validated JSON evidence, retained for 14 days,
even if a check fails. Reports distinguish `pass`, `fail` (a contract mismatch)
and `error` (infrastructure/invalid evidence). Build failures remain visible in
normal build logs. There is no `continue-on-error` or expected-failure exemption.

The runner writes `report.json`, `probe.json` and `control.json` under
`target/harness-runs/<harness>/<run-id>/`, already ignored by Git. Reports include
version, image ID, platform, source/build fingerprints and individual checks.
Containers and private networks are removed after each run; images remain cached.

## Credentials and artifacts

Default/mock mode never reads the host's OpenCode configuration or credential
files. The build context has an explicit source-file allowlist: no `.git`, home
directory, local configuration, or arbitrary repository files. Runtime agent
containers receive only an empty scratch workspace and disposable evidence folder.
They have a read-only root filesystem, an unprivileged user, no Docker socket,
and an internal network without an external route. No host ports are published.

The probe exports only constant identity/signal names and booleans. It never
exports full environments, matched signal values, session IDs, trace IDs, model
credentials, or `Debug` output. This matters because the legacy detector can
still copy `COPILOT_GITHUB_TOKEN` into a signal; removing that rule is separate
work in [issue #5](https://github.com/sdairs/is-ai-agent/issues/5).

Raw CLI transcripts are processed in memory and discarded. Docker runtime logs
are disabled. Unknown artifact fields and non-boolean marker values are rejected.
The workflow uploads the sanitized output directory, never CLI homes or logs.

## Optional live inference (local only)

Live mode is retained for manual provider checks. It is **not exposed by the
GitHub workflow** and is not needed for detection CI. It requires an
OpenAI-compatible streaming chat-completions endpoint with tool calls and Bearer
authentication. Use the exact model ID supported by your endpoint.

```sh
python3 tests/harnesses/run.py --harness pi --mode live \
  --base-url https://YOUR-INFERENCE-HOST/v1 \
  --model YOUR-EXACT-MODEL-ID \
  --token-file /absolute/private/path/inference-token
```

The token file must be outside the repository with mode `600`. Only the gateway
receives it as a read-only runtime mount; the harness receives a dummy local key
and model alias. Only the gateway receives an external network route. The gateway
rejects redirects, suppresses upstream error details, and caps requests at six
and requested output at 2,048 tokens per request. The CLI has a 150-second timeout.
These are request limits, not a billing guarantee. TLS verification stays enabled.
The live route has not been tested against the private ClickHouse endpoint.

## Adding a harness

Add an exact package version/contract to `harnesses.json`, a custom-provider
configuration and normal CLI invocation to `entrypoint.mjs`, a verifier for its
actual execution events to `run.py`, and a matrix entry in the workflow. Extend
the probe's explicit marker/session allowlists only where needed. Include positive
and adversarial verifier fixtures, then run the real container test.

The current adapters all use OpenAI chat completions. Other protocols may need
a new provider adapter. Harnesses requiring a vendor login or hardcoded backend
remain untested under this workflow. Source availability is not the requirement;
configurable model endpoints and an automatable execution surface are.

Unit tests remain the place for broad predicates, precedence, false positives,
and synthetic combinations. Later integration cases can cover repeated commands,
new/resumed sessions, model changes, human commands, PTYs and nested harnesses.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/harnesses -p 'test_*.py'
cargo fmt --check
cargo test --locked
cargo clippy --all-targets -- -D warnings
cargo doc --no-deps
```

References: [Pi provider configuration](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/models.md),
[Pi events](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/json.md),
[Qwen custom authentication](https://qwenlm.github.io/qwen-code-docs/en/users/configuration/auth/),
[Qwen headless mode](https://github.com/QwenLM/qwen-code/blob/main/docs/users/features/headless.md),
[OpenCode custom providers](https://opencode.ai/docs/providers/),
[OpenCode event emission](https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/cli/cmd/run.ts).
