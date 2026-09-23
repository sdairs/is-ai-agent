# Discovering execution signals ourselves

Run an unmodified, pinned harness against the scripted provider, with a probe
inside its real command tool. Compare that with controls before promoting a
variable to a library rule. External detector registries are leads, not evidence.

```sh
python3 tests/harnesses/run.py --harness goose --discover --expect-undetected
python3 tests/harnesses/run.py --harness cline --discover --expect-undetected
python3 tests/harnesses/run.py --harness pi --discover
```

`--discover` works with every adapter and only in mock mode. CI runs it for all
sixteen CLIs on PRs, manual runs and releases. It adds `discovery.json` and a configured
control to the normal evidence directory; Cline also has a non-agent control.
Discovery does not change `detect()` or make a detection gap pass.

## Controls and collected evidence

1. **Clean shell:** harness installed, no harness configuration or agent running.
2. **Configured environment:** the same environment and disposable configuration
   used to launch the harness, before starting the agent. This separates inherited
   provider settings from variables the harness adds.
3. **Agent tool:** the normal model-requested shell tool executes the Rust probe.
   Both its detection result and its discovery output must match the fresh files
   and nonce in the tool result observed by the provider/event verifier.
4. **Non-agent command where available:** Cline runs `cline skill list`. Its `npx`
   dependency is replaced with an argument-checking probe, so the real Cline code
   launches our child without downloading a skills package or starting an agent
   turn. This is a dependency fixture, not an end-to-end test of the skills CLI.

The configured baseline exists only in the container's private `/tmp` filesystem.
The helper compares values there and exports portable environment names,
`added`/`changed`/`removed`/`unchanged`, nonblank booleans and exact values.
Nothing is redacted or normalized: mock API keys, generated session IDs, paths
and unfamiliar values are all preserved. Only isolated mock runs support discovery;
no real provider credential, host environment or user configuration is supplied.
An optional diagnostic process chain is represented using a fixed list of
executable names plus `other`/`unavailable`. It is not used by the library.
Invalid names are omitted; strict artifact schemas reject extra fields or values.
No private provider config, host environment, or real credential is supplied.

## Goose 1.51.0: a generic session ID, no identity

In the Linux built-in developer `shell` tool, the only added non-shell variable
was `AGENT_SESSION_ID`. `GOOSE_TERMINAL`, `AGENT`, and `AI_AGENT` were absent.
`GOOSE_PROVIDER`, `GOOSE_MODEL`, and the other Goose settings were unchanged from
the configured control. `PWD`, `SHLVL`, and `_` are ordinary shell bookkeeping.

The [pinned shell implementation](https://github.com/aaif-goose/goose/blob/v1.51.0/crates/goose/src/agents/platform_extensions/developer/shell.rs#L682)
matches the observation: `apply_session_environment` injects `AGENT_SESSION_ID`
but no Goose-specific identity. The diagnostic parent executable was `goose`.

**Decision:** keep the detection gap. A generic session variable cannot identify
Goose; provider settings would classify the configured control as an agent.
Process ancestry is outside the current library contract. This is evidence about
the pinned built-in developer tool, not every historical release or MCP backend.
A future fix needs a tool-owned product marker, ideally an upstream documented
export, followed by a new probe run. Session extraction can be considered
separately after identity and session lifecycle semantics are established.

## Cline CLI 3.0.64: launch metadata also appears without an agent turn

Neither `CLINE_ACTIVE` nor `CLINE_TASK_ID` appeared. The discovery probe found:

| Variable | Configured control | Agent `run_commands` | Non-agent `cline skill list` child |
| --- | --- | --- | --- |
| `CLINE_WRAPPER_PATH` | Absent | Added, nonblank | Added, nonblank |
| `CLINE_CONNECTOR_CLI_LAUNCH` | Absent | Added, nonblank | Added, nonblank |
| `NODE_EXTRA_CA_CERTS` | Absent | Added, nonblank | Added, nonblank |

Source was checked at release tag `cli-v3.0.64`, commit
`844c30d7ea3e01df3c036729d8c78a2678275aee`:

- The [npm wrapper](https://github.com/cline/cline/blob/844c30d7ea3e01df3c036729d8c78a2678275aee/apps/cli/bin/cline#L19)
  sets its own path and configures CA certificates for the compiled child.
- The [entrypoint](https://github.com/cline/cline/blob/844c30d7ea3e01df3c036729d8c78a2678275aee/apps/cli/src/index.ts#L44)
  records connector launch metadata before dispatching CLI commands. Its
  [setter](https://github.com/cline/cline/blob/844c30d7ea3e01df3c036729d8c78a2678275aee/sdk/packages/shared/src/runtime/hub-daemon-env.ts#L68)
  serializes launch configuration into the environment.
- The [shell executor](https://github.com/cline/cline/blob/844c30d7ea3e01df3c036729d8c78a2678275aee/sdk/packages/core/src/extensions/tools/executors/bash.ts#L674)
  inherits the process environment, as does the non-agent
  [skill command](https://github.com/cline/cline/blob/844c30d7ea3e01df3c036729d8c78a2678275aee/apps/cli/src/commands/skill.ts#L115).

**Decision:** keep the detection gap. Either Cline variable, or their combination,
would also label the non-agent child as agent execution. Their presence identifies
Cline ancestry, not who requested the command. No new default rule is justified.
This does not establish the behavior of Cline's separate VS Code extension.

## How to evaluate the next candidate

Start with the same discovery mode. Review names that appear only in the tool
environment; reject configuration-only and shared shell variables. Trace a
promising candidate to the exact released source when available. If its value
matters, inspect the captured value and add an explicit probe predicate if needed.
Add a real negative control for that launch surface, then check another fresh
run, other supported backends, and session/resume/nesting behavior as relevant.
Only then add a narrow rule and regression tests. Discovery never automatically
imports a candidate into the detector.

The [generated inventory](inventory/README.md) provides a versioned reference
sheet of harnesses, their variable names and exact values. Weekly reports
compare it with new observations and propose inventory-only PRs. Detection results,
controls and changes from the launch baseline remain in the test reports. Generic
`AGENT` / `AI_AGENT` identities are observed even when another signal wins, so
adoption alongside an older marker is visible. Signal changes with preserved
detection are review items, not automatic upstream bug reports.

Historical name-only Linux ARM64 snapshots: [Goose](evidence/goose-1.51.0-discovery.json)
and [Cline](evidence/cline-3.0.64-discovery.json). Each records the version, image
and source fingerprints, controls, observations, and successful tool roundtrip.

The current suite does not cover all human-command, PTY, IDE, nested, or resumed
session paths. The evidence is intentionally scoped to the recorded versions,
platforms and commands. See the historical name-only discovery reports in
[evidence](evidence/) and the per-run GitHub Actions artifacts.

## Expanded probes (2026-09-23)

| CLI | Observed predicate | Library decision |
| --- | --- | --- |
| DeepSeek Harness 0.1.5-rc.3 | `DSH_SHELL == "1"`; `DSH_SESSION_ID` present | Add exact identity rule and nonblank session extraction; session alone does not identify the human web terminal |
| Kilo 7.7.9 | `KILO == "1"` alongside `OPENCODE` | Identify Kilo before the inherited OpenCode fallback |
| OpenClaw 2026.9.5 | `OPENCLAW_SHELL == "exec"` | Add exact rule; reject `tui-local`, `acp-client`, `acp` and other values |
| Hermes 0.21.4 | `AI_AGENT` identifies Hermes; `HERMES_AGENT == "true"`; session present | Add generic aliases, exact marker and nonblank session extraction |
| VTCode 0.169.1 | `VTCODE == "1"` | Add exact rule; tested `exec` with supported single orchestration mode |
| Junie 26.9.7 (3110.7) | `JUNIE_SHIM_PATH`, `MATTERHORN_SESSION_ID` present | Retain as candidates, no default identity/session rule yet |

The detection probe checks literal predicates inside the container and exports
booleans. Discovery additionally records exact environment values, including
arbitrary strings and generated session identifiers. Positive results require
clean/configured negative controls and the same fresh output in both the artifact
and actual tool result. Rust fixtures cover wrong values and precedence; they are
not presented as real tests of other human/IDE/ACP modes.

Junie's headless custom-provider path is verified. The official shim exports its
path before command dispatch, so presence alone has weaker semantics than a marker
injected only by an agent tool. The interactive `!` control attempt did not produce
a usable probe; the distinction remains unresolved. `MATTERHORN_SESSION_ID` is a
new research lead from our own invocation, not yet a session API promise.

Goose was also tested at **1.52.0**, now the manifest pin, with the same missing
markers. The developer-shell rewrite in
[PR #7466](https://github.com/aaif-goose/goose/pull/7466) removed the old injection;
1.26.0 had the markers and 1.27.0 included the replacement shell. The upstream
request to restore them is [Goose #12470](https://github.com/aaif-goose/goose/issues/12470).

Use `compare.py` on two successful-execution discovery reports for the same CLI
and platform to review drift. A new CLI requires a manifest entry and normal
launcher configuration; a new version of an existing npm adapter can first be
tried with `run.py --version`. CI derives its jobs from the manifest.
