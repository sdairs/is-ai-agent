# Real harness integration tests

These tests install **unmodified, pinned CLI releases inside Docker**, point
those CLIs at a local scripted model provider, and ask their real shell tools to
run a Rust probe linked against this repository. No LLM, vendor account or real
credential is needed. The same runner works with OrbStack locally and Docker on
GitHub-hosted Linux runners.

| Harness | Pinned version | Real tool | Detection / session contract |
| --- | --- | --- | --- |
| Pi | 0.87.1 | `bash` | Detected; `PI_SESSION_ID` |
| Qwen Code | 0.24.4 | `run_shell_command` | Detected; `QWEN_CODE_SESSION_ID` |
| OpenCode | 1.18.32 | `bash` | Detected; no session ID asserted |
| GitHub Copilot CLI | 1.0.88 | `bash` | Detected; `COPILOT_AGENT_SESSION_ID` |
| Crush | 0.96.1 | `bash` | Detected; no session ID asserted |
| Codex CLI | 0.156.1 | `exec_command` | Detected; `CODEX_THREAD_ID` |
| Claude Code | 2.1.280 | `Bash` | Detected; `CLAUDE_CODE_SESSION_ID` |
| Gemini CLI | 0.60.0 | `run_shell_command` | Detected; no session ID asserted |
| Goose | 1.51.0 | `shell` (built-in developer extension) | **Known gap:** command runs, library returns `None` |
| Cline CLI | 3.0.64 | `run_commands` | **Known gap:** command runs, library returns `None` |

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
python3 tests/harnesses/run.py --harness codex
python3 tests/harnesses/run.py --harness claude-code
```

Choose any harness ID in the manifest. The first build downloads public images
and a published npm package (or a checksum-verified Goose release binary). Subsequent
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

The fake provider implements scripted Chat Completions, Responses, Anthropic
Messages and Gemini API responses.
It chooses the shell tool from the CLI's advertised tools and requests exactly
one probe command. The CLI performs the command execution itself. The provider
returns a final text response after receiving the tool result.

A detection pass requires all of the following:

1. The plain-shell control detects no agent.
2. The CLI executes the exact command once, emits a successful tool result, and
   finishes successfully with exit code zero.
3. The tool output matches the freshly written probe artifact and run nonce.
4. The library identifies the expected harness using its actual markers.
5. The harness supplies the expected markers/session context, and the library
   returns the matching session ID (or none where the table specifies it).

For Pi, Qwen Code and OpenCode, CLI events establish the command/result link.
For the other adapters, the gateway records the requested shell tool and command,
then observes the matching tool result in the CLI's next API request. The runner
compares that result with the probe file and checks that the CLI finishes normally.
The gateway retains this evidence in memory only; it never runs the command itself.

The runner does not set identity or session markers. A clean container prevents
ambient Codex/CI environment variables from contaminating attribution. A model
saying “done”, an unrelated tool result, stale file, wrong command, or nonzero
exit cannot pass. This is regression evidence for cooperative software, not
cryptographic attestation against an agent deliberately forging artifacts.

The Pi test initially exposed missing session extraction in `is-ai-agent` 0.5.0;
this change adds its nonblank session fallback/extraction and focused unit tests.
The [historical report](evidence/pi-0.87.1-mock.json) records the original failure.
New runs test the fixed implementation.

## Known detection gaps

Goose 1.51.0 and Cline CLI 3.0.64 both execute the command and return the matching
probe output, but `detect()` returns `None` in the tested Linux CLI environment.
Goose supplies neither `GOOSE_TERMINAL` nor a recognised generic identity;
Cline supplies neither `CLINE_ACTIVE` nor `CLINE_TASK_ID`. No marker is injected
to make these tests pass, and no provider configuration is promoted to an identity
rule. This observation does not certify other launch modes or IDE extensions.
Goose was also checked with `--no-session`; the default saved-session run has the
same identity gap. The committed adapter uses a normal saved session.
Sanitized local snapshots: [Goose](evidence/goose-1.51.0-mock.json) and
[Cline](evidence/cline-3.0.64-mock.json).

Our [discovery investigation](discovery.md) compares configured, agent-tool and
non-agent environments. Goose adds a generic `AGENT_SESSION_ID`; Cline adds
launcher variables that also appear in a non-agent `cline skill list` child.
Neither observation justifies a new default identity rule. The reusable
`--discover` mode records redacted environment differences and diagnostic process
ancestry so we can find and evaluate signals ourselves.

Running either adapter normally exits nonzero and reports `fail`. CI explicitly
uses the documented observation mode:

```sh
python3 tests/harnesses/run.py --harness goose --expect-undetected
python3 tests/harnesses/run.py --harness cline --expect-undetected
```

These jobs are labelled **known detection gap** and reports say `known-gap`,
never `pass`. They must still execute the exact command successfully, return its
matching fresh output, have no agent in the control shell, and produce exactly
the expected absence of detection/session/identity markers. Infrastructure errors,
failed commands, unexpected attribution, or newly appearing expected markers fail
CI. When detection becomes possible, remove the known-gap entry and switch the
adapter to an ordinary detection test.

## GitHub Actions

[Harness integration tests](../../.github/workflows/harness-tests.yml) runs on
pull requests, pushes to `main`, and manual dispatch. A separate matrix job runs
each harness; one failure does not cancel the others. It also runs Rust tests,
formatting, Clippy, documentation generation, and the Python verifier/gateway tests.
Every matrix job enables `--discover`, including its configured-environment
negative control and Cline's non-agent command control.

[The release workflow](../../.github/workflows/release.yml) calls the same
reusable workflow and requires it to pass **before publishing to crates.io**.
No inference secrets are passed to these jobs. Checkout does not persist GitHub
credentials. The publishing token is still confined to the publish step.

Each matrix job uploads only schema-validated JSON evidence, retained for 14 days,
even if a check fails. Reports distinguish `pass`, `fail` (a contract mismatch)
and `error` (infrastructure/invalid evidence). The two explicitly labelled discovery
jobs can also report `known-gap`, as described above. Build failures remain visible
in normal build logs. There is no blanket `continue-on-error` exemption.

The runner writes `report.json`, `probe.json` and `control.json` under
`target/harness-runs/<harness>/<run-id>/`, already ignored by Git. Reports include
version, image ID, platform, source/build fingerprints and individual checks.
Containers and private networks are removed after each run; images remain cached.
Discovery adds `discovery.json`, `configured_control.json`, and (for Cline)
`non_agent_control.json`. It is also available locally for any mock adapter:
`python3 tests/harnesses/run.py --harness pi --discover`.

## Credentials and artifacts

Default/mock mode never reads the host's OpenCode configuration or credential
files. The build context has an explicit source-file allowlist: no `.git`, home
directory, local configuration, or arbitrary repository files. Runtime agent
containers receive only an empty scratch workspace and disposable evidence folder.
The disposable `/tmp` permits execution because Copilot extracts a native module
there; it is size-limited and disappears with the container. They have a read-only
root filesystem, an unprivileged user, no Docker socket,
and an internal network without an external route. No host ports are published.

The detection probe exports only constant identity/signal names and booleans. It never
exports full environments, matched signal values, session IDs, trace IDs, model
credentials, or `Debug` output. This matters because the legacy detector can
still copy `COPILOT_GITHUB_TOKEN` into a signal; removing that rule is separate
work in [issue #5](https://github.com/sdairs/is-ai-agent/issues/5).
Discovery additionally exports valid environment variable names, change categories,
nonblank booleans and allowlisted executable names. Its raw comparison baseline
stays in the disposable container tmpfs; values, hashes, paths and process
arguments are never included in artifacts. Discovery is disabled in live mode.

Raw CLI transcripts are processed in memory and discarded. Docker runtime logs
are disabled. Unknown artifact fields and non-boolean marker values are rejected.
Provider-side tool evidence is also processed in memory and discarded. Its read
endpoint exists only in mock mode on the private container network. The workflow
uploads the sanitized output directory, never CLI homes or logs.

## Optional live inference (local only)

Live mode is retained for manual provider checks. It is **not exposed by the
GitHub workflow** and is not needed for detection CI. It requires an
OpenAI-compatible streaming chat-completions endpoint with tool calls and Bearer
authentication. It is currently supported only by the original Pi, Qwen Code and
OpenCode adapters; the seven additional adapters require mock mode. Use the exact
model ID supported by your endpoint.

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
configuration and normal CLI invocation to `entrypoint.mjs`, either a verifier
for its actual execution events or the correlated provider roundtrip verifier in `run.py`, and a matrix entry in the workflow. Extend
the probe's explicit marker/session allowlists only where needed. Include positive
and adversarial verifier fixtures, then run the real container test.

The current gateway covers four protocols. Other protocols may need
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

Additional adapter references:
[Copilot offline/custom-provider authentication](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/authenticate-copilot-cli),
[Crush providers](https://github.com/charmbracelet/crush#custom-providers),
[Codex providers](https://learn.chatgpt.com/docs/config-file/config-reference),
[Claude gateway protocol](https://code.claude.com/docs/en/llm-gateway-protocol),
[Gemini endpoint configuration](https://geminicli.com/docs/reference/configuration/),
[Goose shell source at v1.51.0](https://github.com/aaif-goose/goose/blob/v1.51.0/crates/goose/src/agents/platform_extensions/developer/shell.rs),
[Cline CLI](https://github.com/cline/cline/blob/main/apps/cli/README.md).
