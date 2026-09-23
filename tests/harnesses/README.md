# Real harness integration tests

These tests install **unmodified, pinned CLI releases inside Docker**, point
those CLIs at a local scripted model provider, and ask their real shell tools to
run a Rust probe linked against this repository. No LLM, vendor account or real
credential is needed. The same runner works with OrbStack locally and Docker on
GitHub-hosted Linux runners.

| Harness | Pinned version | Real tool | Detection / session contract |
| --- | --- | --- | --- |
| Pi | 0.87.1 | `bash` | Detected; `PI_SESSION_ID` |
| Qwen Code | 0.24.4, also 0.24.3 | `run_shell_command` | Detected; `QWEN_CODE_SESSION_ID` |
| OpenCode | 1.18.32 | `bash` | Detected; no session ID asserted |
| GitHub Copilot CLI | 1.0.88 | `bash` | Detected; `COPILOT_AGENT_SESSION_ID` |
| Crush | 0.96.1 | `bash` | Detected; no session ID asserted |
| Codex CLI | 0.156.1 | `exec_command` | Detected; `CODEX_THREAD_ID` |
| Claude Code | 2.1.280 | `Bash` | Detected; `CLAUDE_CODE_SESSION_ID` |
| Gemini CLI | 0.60.0 | `run_shell_command` | Detected; no session ID asserted |
| DeepSeek Harness | 0.1.5-rc.3 | `bash` | Detected via `DSH_SHELL=1`; `DSH_SESSION_ID` |
| Kilo Code | 7.7.9 | `bash` | Detected via `KILO=1`, ahead of inherited OpenCode markers |
| OpenClaw | 2026.9.5 | `exec` (`agent exec`, direct code mode) | Detected via `OPENCLAW_SHELL=exec` |
| Hermes Agent | 0.21.4 (release v2026.9.21) | `terminal` (local backend) | Detected; `HERMES_SESSION_ID` |
| VTCode | 0.169.1 | `exec_command` (single orchestration mode) | Detected via `VTCODE=1` |
| Junie | npm 3110.7.0 / binary 26.9.7 (3110.7) | `bash`, then `submit` | **Pending rule:** real command works; launcher/session candidates need further controls |
| Goose | 1.52.0 | `shell` (built-in developer extension) | **Known gap:** command runs, library returns `None` |
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
and a published npm package or checksum-verified release archive. Hermes uses its
supported editable installation from an immutable, checksum-verified source snapshot. Subsequent
builds reuse Docker's cache. VTCode uses its official static musl archive on
x86 Linux: its GNU archive needs glibc 2.39, newer than the test base image. `--skip-build` reuses an existing image only when its
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
returns a final response after receiving the tool result (Junie requires its
advertised `submit` tool to terminate normally).

A detection pass requires all of the following:

1. The plain-shell control detects no agent.
2. The CLI executes the exact command once, emits a successful tool result, and
   finishes successfully with exit code zero.
3. The tool output matches the freshly written probe artifact and run nonce.
4. The library identifies the expected harness using its actual markers.
5. The harness supplies the expected markers/session context, and the library
   returns the matching session ID (or none where the table specifies it).
   Value-sensitive rules use explicit boolean predicate results (`exact_markers`),
   so a nonblank but wrong marker value cannot pass.

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

Goose 1.52.0 and Cline CLI 3.0.64 both execute the command and return the matching
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
`--discover` mode records exact environment differences and diagnostic process
ancestry so we can find and evaluate signals ourselves.

Junie also executes the real probe and completes through its `submit` tool.
We observed `JUNIE_SHIM_PATH` and `MATTERHORN_SESSION_ID`, but have not yet
established an agent-only predicate or session lifecycle contract. The shim
sets its marker before command dispatch. A trial of the interactive human `!`
path did not produce a usable control; it is **not** evidence of absence.
Junie therefore remains a discovery/known-gap job, with its observed candidate
markers required to stay present, and no new Junie library rule yet.

Running these adapters normally exits nonzero and reports `fail`. CI explicitly
uses the documented observation mode:

```sh
python3 tests/harnesses/run.py --harness goose --expect-undetected
python3 tests/harnesses/run.py --harness cline --expect-undetected
python3 tests/harnesses/run.py --harness junie --expect-undetected
```

These jobs are labelled **known detection gap** and reports say `known-gap`,
never `pass`. They must still execute the exact command successfully, return its
matching fresh output, have no agent in the control shell, and produce exactly
the expected absence of detection/session attribution. Goose and Cline assert absent
identity markers; Junie instead asserts its pending candidates remain present. Infrastructure errors,
failed commands, unexpected attribution, or newly appearing expected markers fail
CI. When detection becomes possible, remove the known-gap entry and switch the
adapter to an ordinary detection test.

## GitHub Actions

[Harness integration tests](../../.github/workflows/harness-tests.yml) runs on
pull requests, pushes to `main`, and manual dispatch. A separate matrix job runs
each pinned harness/version, read directly from the manifest; one failure does not cancel the others. It also runs Rust tests,
formatting, Clippy, documentation generation, and the Python verifier/gateway tests.
Every matrix job enables `--discover`, including its configured-environment
negative control and Cline's non-agent command control.

[The release workflow](../../.github/workflows/release.yml) calls the same
reusable workflow and requires it to pass **before publishing to crates.io**.
No inference secrets are passed to these jobs. Checkout does not persist GitHub
credentials. The publishing token is still confined to the publish step.

Each matrix job uploads only schema-validated JSON evidence, retained for 14 days,
even if a check fails. Reports distinguish `pass`, `fail` (a contract mismatch)
and `error` (infrastructure/invalid evidence). The explicitly labelled discovery
jobs can also report `known-gap`, as described above. Build failures remain visible
in normal build logs. There is no blanket `continue-on-error` exemption.

### Pinned regression checks and upstream monitoring

Use three complementary sets of cases:

| Check | Version selection | Purpose |
| --- | --- | --- |
| Every PR and release | Reviewed primary pin for every harness | Catch library or adapter regressions against known CLI behavior |
| Every PR and release | Optional `compatibility_versions` per harness | Keep selected older releases working; Qwen 0.24.3 is the first extra case |
| Weekly or manual | Fresh primary pin versus freshly resolved `latest` | Find upstream changes without changing the reviewed contracts |

Latest-only checks move independently of a PR: a rerun might install a different
CLI, and upstream changes can block an unrelated library release. Pins make the
CLI versions repeatable and retain coverage for older users. They do not fully
lock transitive installer dependencies; image and source fingerprints remain part
of the evidence. Add older cases where there is a compatibility promise or an
interesting change, rather than testing every published version.

[Upstream harness changes](../../.github/workflows/harness-watch.yml) runs on
Saturdays at 08:17 UTC, or manually with a harness ID (`all` by default) and
candidate (`latest` by default). It also runs on PRs that change the watcher
itself. This workflow is separate from the pinned release gate. Each harness job
resolves the public release once, records exact versions and npm integrity or
archive checksums, then runs **both** versions with the same library/probe and
platform. It does not rewrite the manifest or silently accept new observations.

For npm, `latest` means the publisher's `latest` tag, which can point to a release
candidate. For GitHub binaries/source, it means GitHub's latest stable release;
Hermes tags are resolved to immutable commits. Junie's npm version is mapped to
the expected binary version separately. A missing asset, changed version scheme,
or incompatible provider protocol is a resolution/execution problem, not evidence
of a removed marker. The resolver can use an existing local `gh` login, or the
workflow's read-only GitHub token, for public GitHub metadata. That credential is
never passed into Docker builds or runtime containers.

The job summary classifies the result:

- `unchanged`: detection and environment observations agree, including expected absence.
- `detection_regression`: a previously detected identity disappears or changes.
- `new_detection`: a known gap now produces an identity with the current library.
- `new_candidates`: new nonblank environment names appear in the agent tool;
  names also observed in the available non-agent control are excluded as candidates.
- `contract_changed` / `observations_changed`: marker predicates, session checks,
  control checks, or other environment observations differ.
- `baseline_failed`, `execution_failed`, or `resolution_or_evidence_error`:
  the comparison could not establish the required execution evidence.

Every delta or execution/resolution failure makes its watcher job fail so it is
visible in Actions and normal GitHub workflow notifications. Per-harness artifacts retain resolved build
metadata, both validated reports, the structured comparison and Markdown summary
for 90 days. Investigate a candidate with source and non-agent controls before
adding an identity rule. All variable values are recorded exactly. Generated
session IDs, container hostnames and temporary paths can change on every run;
these appear in comparisons too and are not evidence of a detection regression.
A new name is a lead, not proof of an agent-only marker.

### Versioned inventory and review issues

The [generated reference sheet](inventory/README.md) and [structured inventory](inventory/observed.json)
record the latest reviewed observations for every harness. These files are read
only by the inventory/reporting tools: the library, build context, detection
contracts and pinned test assertions never consume them. Git history preserves
earlier observations after inventory PRs are merged.

The JSON is simply **harness → variable → value**. It includes every portable
variable present in the command environment, including inherited configuration
and empty strings. There are no detection summaries, controls, versions or run
metadata in the inventory; those remain in the CI reports and artifacts.

The collector preserves every value exactly, including unfamiliar strings, dummy
API keys, paths and generated session IDs. There is no redaction, value allowlist,
truncation or ID normalization. Discovery is restricted to isolated mock runs:
no real provider credentials, host environment or user configuration are supplied.
JSON retains the exact strings; the reference sheet escapes them only for display.
Variable names must match `[A-Za-z_][A-Za-z0-9_]{0,95}`; invalid/long names are
omitted, and more than 256 names fails validation rather than silently truncating.
Removed variables are absent from the inventory; their removal appears in the delta.

The aggregation job runs even when individual watchers report a delta or fail.
It compares this week's latest variables and values with the **checked-in inventory**.
The separate pinned-versus-latest comparison still checks detection and controls.
A verified command with a changed detection contract can update an observation.
An installation, execution, missing-artifact or invalid-evidence failure retains
that harness's previous entry and reports it as unavailable, never as a removed marker.

For scheduled runs, or manual `all` / `latest` runs on the default branch, a
separate publisher opens or updates an inventory-only PR on
`codex/harness-inventory`. Its tree can change only the two generated files. It
does not commit to the default branch, change rules, rewrite the manifest, force
push, or automatically merge. It rejects a stale default branch or unrelated
changes on its proposal branch. PR and single-harness/version trials only produce
downloadable inventory previews; they cannot publish.

Variable additions, removals and value changes create an investigation issue with
the before/after delta, tested versions, evidence link and inventory PR. Detection
changes and unavailable probes also create issues, even if the inventory is
unchanged. Reports are observations, not diagnoses of an upstream defect: review
whether a change is a compatible migration, a rule to add, a collector
change, or a possible regression.

A new CLI version alone creates no inventory PR or issue when variables, values
and test results agree. Matching issues are updated rather than duplicated;
closed issues are treated as acknowledged rather than reopened. An obsolete
inventory PR is closed only when a complete run again matches main. Full fresh
artifacts and the combined report remain available for 90 days.

The publisher is isolated from the probe jobs and receives only the repository's
GitHub token. It requires contents, issues and pull-request write permissions;
the repository setting **Allow GitHub Actions to create and approve pull requests**
must allow PR creation. The workflow never approves a PR. GitHub-token-created
PRs do not themselves trigger another workflow run; inventory schemas and scope
are checked before publication. See [GitHub token behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).

To generate a preview from downloaded watcher artifacts:

```sh
python3 tests/harnesses/inventory.py --artifacts /path/to/downloaded/artifacts \
  --run-url https://github.com/OWNER/REPO/actions/runs/RUN_ID
```

The output is `target/harness-inventory/`: JSON, the reference sheet, structured
delta, and a readable summary. No GitHub write happens in this command.

The schedule starts only after this workflow reaches the default branch. GitHub
may delay scheduled runs and disables schedules in inactive public repositories
after 60 days; see [GitHub's schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

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
Discovery exports valid environment variable names, their complete values, change
categories, nonblank booleans and allowlisted executable names. Mock API keys,
container paths and generated IDs are retained unmodified. Its comparison baseline
file stays in the disposable container tmpfs. Discovery is disabled in live mode;
the optional live gateway's real credential never enters the agent container or image.

Raw CLI transcripts are processed in memory and discarded. Docker runtime logs
are disabled. Unknown artifact fields and non-boolean marker values are rejected.
Provider-side tool evidence is also processed in memory and discarded. Its read
endpoint exists only in mock mode on the private container network. The workflow
uploads the validated output directory, never CLI homes or logs.

## Optional live inference (local only)

Live mode is retained for manual provider checks. It is **not exposed by the
GitHub workflow** and is not needed for detection CI. It requires an
OpenAI-compatible streaming chat-completions endpoint with tool calls and Bearer
authentication. It is currently supported only by the original Pi, Qwen Code and
OpenCode adapters; the other adapters require mock mode. Use the exact
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

## Trial a version and compare observations

To resolve and compare in one command (all CLI installation stays in Docker):

```sh
python3 tests/harnesses/watch.py --harness goose
python3 tests/harnesses/watch.py --harness qwen-code --candidate 0.24.3
```

The watcher writes `target/harness-watch/<harness>/<run-id>/`. Its exit status is
zero only for `unchanged`; other outcomes require review. Exact candidates are
supported for npm packages, Goose and VTCode. Hermes uses `latest` here because
its release tags differ from its package version; testing a specific historical
Hermes release requires explicit source metadata in the manifest.

For npm adapters without separate binary metadata, `--version` overrides the
pin **only for that run**. It validates an exact version, builds that version,
checks the CLI's reported version and retains the existing signal contract.
It does not edit the repository or accept `latest`/version ranges.

```sh
python3 tests/harnesses/run.py --harness qwen-code --discover
python3 tests/harnesses/run.py --harness qwen-code --version 0.24.3 --discover
python3 tests/harnesses/compare.py /path/to/before/report.json /path/to/after/report.json
```

The comparison requires verified real command execution on the same harness and
platform. It compares identity, signal, marker predicates, session matches and
exact environment observations. Exit codes: 0 unchanged, 1 drift, 2 invalid or
incomplete evidence. It ignores timestamps, nonces and image IDs. A new variable
is a research lead, not an automatically accepted rule. Older probe schemas can
produce an expected diff when newly collected boolean fields appear.

After review, update the pin in `harnesses.json` and open a PR; the full CI matrix
checks it again. To retain an older release in that matrix, add an override to its
`compatibility_versions` array, for example `{"version": "0.24.3"}`. Overrides
inherit the primary detection contract but can declare their own expectations
when historical behavior differs. Goose/VTCode release assets, Hermes source
snapshots and Junie's separate binary version require explicit matching metadata
in each compatibility override. `run.py --version` accepts the primary pin and
reviewed compatibility entries, and refuses unlisted versions needing that extra
metadata. The watcher can resolve the metadata for a prospective bump.
Dependencies downloaded by package installers are not a complete hermetic lock;
reports retain image/source fingerprints for that reason.

## Adding a harness

Add an exact package version/contract to `harnesses.json`, a custom-provider
configuration and normal CLI invocation to `entrypoint.mjs`, either a verifier
for its actual execution events or the correlated provider roundtrip verifier in `run.py`. CI includes every manifest entry automatically. Extend
the probe's explicit marker/session allowlists only where needed. Record the exact
CLI mode and its source/docs, run discovery before changing the library, investigate
non-agent controls, then add a narrow predicate and false-positive/precedence tests. Include positive
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

New adapter references: [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness),
[Kilo CLI](https://github.com/Kilo-Org/kilocode),
[OpenClaw standalone agent](https://github.com/openclaw/openclaw/blob/v2026.9.5/docs/cli/agent.md),
[Hermes pinned source](https://github.com/NousResearch/hermes-agent/tree/d337b736aa1e8ebecfab043842d13e4a2d2f48a3),
[VTCode orchestration modes](https://github.com/vinhnx/VTCode/blob/0.169.1/crates/codegen/vtcode-config/src/core/agent.rs),
[Junie custom model profiles](https://junie.jetbrains.com/docs/custom-llm-models.html).

This suite now exercises sixteen CLIs. Library entries outside this manifest
remain **unverified by real invocation here**: Cursor surfaces, Augment, Trae,
Amp, Devin, Replit, Antigravity, iFlow, Amazon Q, Roo Code, Cowork, CodeBuddy,
Grok CLI, Warp, Kiro, Firebender, OpenHands, veCLI and v0. This is a coverage
inventory, not a claim that those products cannot be automated. Each needs a
suitable isolated launch mode and configurable provider before joining this lab.
