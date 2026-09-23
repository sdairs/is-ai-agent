# is-ai-agent

Detect whether a CLI is being invoked by an AI coding agent, and identify which one.

Inspired by the [`AGENT` environment variable proposal](https://github.com/agentsmd/agents.md/issues/136). Lets your CLI adapt its output — structured errors, more verbose tracebacks, no interactive prompts — when it's running under an agent rather than a human.

## Install

```toml
[dependencies]
is-ai-agent = "0.5"
```

## Usage

```rust
use is_ai_agent::{detect, is_ai_agent};

if is_ai_agent() {
    // emit structured/agent-friendly output
}

if let Some(agent) = detect() {
    eprintln!("running under {}", agent.name);
    // URL-safe slug, e.g. "claude-code"
    let slug = agent.id.as_str();
    // Stable id for this agent run, when the agent publishes one.
    if let Some(session) = &agent.session_id {
        eprintln!("session: {session}");
    }
    // Active W3C trace context, when present — forward it downstream.
    if let Some(trace_id) = agent.trace_id() {
        eprintln!("trace: {trace_id}");
    }
}
```

### Session id

Many agentic CLIs expose a stable identifier for the current session/conversation to the subprocesses they spawn. `Agent::session_id` surfaces it as a single unified field, so a downstream tool can stamp it onto outbound requests (headers, query comments) and a backend can correlate every call that belongs to the same agent run.

The value is opaque and only comparable *within the same agent* — pair it with `agent.id` before correlating. It is `None` when the detected agent doesn't publish one.

| Agent | Source env var | Notes |
|---|---|---|
| Claude Code / Claude Cowork | `CLAUDE_CODE_SESSION_ID` | Per-conversation UUID; shared by sub-agents and all spawned subprocesses. |
| CodeBuddy | `CODEBUDDY_SESSION_ID`, then `CLAUDE_SESSION_ID` | Dual-written to a `CLAUDE_*` mirror. |
| OpenAI Codex | `CODEX_THREAD_ID` | |
| Amp | `AMP_CURRENT_THREAD_ID`, then `AGENT_THREAD_ID` | |
| Qwen Code | `QWEN_CODE_SESSION_ID` | |
| Cursor / Cursor CLI | `CURSOR_TRACE_ID` | Trace id; per-session vs per-command scope is undocumented, so correlation may fragment. |
| GitHub Copilot | `COPILOT_AGENT_SESSION_ID`, then `COPILOT_AGENT_JOB_ID` | Job id is set by the Actions-based cloud coding agent. |
| Warp | `OZ_RUN_ID` | Run id; scope undocumented, so correlation may fragment. |
| Cline | `CLINE_TASK_ID` | |
| Roo Code | `ROO_CODE_TASK_ID` | |
| DeepSeek Harness | `DSH_SESSION_ID` | Read only after identifying the agent shell; the session variable alone is not identity. |
| Hermes Agent | `HERMES_SESSION_ID` | Read after identifying Hermes; verified in the local terminal backend. |
| Pi | `PI_SESSION_ID` | Injected by shell tools; human `!` / `!!` commands do not receive this session metadata. |

Gemini CLI, Crush, and Grok CLI expose a session id only to *hooks*, not to ordinary subprocesses, so no id is available there.

### Trace context

When the agent runs under [OpenTelemetry tracing](https://www.w3.org/TR/trace-context/), it may publish a `TRACEPARENT` to its subprocesses. `Agent::traceparent` exposes the raw W3C value (forward it as a `traceparent` header to keep downstream requests on the same distributed trace), and `Agent::trace_id()` extracts just the 32-hex trace-id correlation key.

`TRACEPARENT` is a standard var name, so it's read directly rather than per agent. Among the agents here, **Claude Code** and **Qwen Code** propagate it — both gated behind telemetry being enabled, and off by default (Claude Code additionally requires `CLAUDE_CODE_PROPAGATE_TRACEPARENT`; Qwen Code requires `outboundCorrelation.propagateTraceContext`). For other agents a `traceparent` appears only if one was already present in the ambient shell and inherited.

For tests or callers that want to consult a captured environment instead of the live process, use `detect_with`:

```rust
use is_ai_agent::detect_with;

let agent = detect_with(
    |name| if name == "AGENT" { Some("goose".into()) } else { None },
    |_| false,
);
```

## Detection order

1. The generic `AGENT` (the [agents.md proposal](https://github.com/agentsmd/agents.md/issues/136)) and `AI_AGENT` ([@vercel/detect-agent](https://www.npmjs.com/package/@vercel/detect-agent)) env vars, when their value names a known agent (`goose`, `amp`, `claude-code`, `cowork`, `cursor`, `cursor-cli`, `gemini-cli`, `codex`, `augment`, `cline`, `opencode`, `trae`, `devin`, `replit`, `antigravity`, `github-copilot`, `crush`, `qwen-code`, `iflow-cli`, `amazon-q-cli`, `roo-code`, `codebuddy`, `grok-cli`, `warp`, `pi`, `kiro`, `firebender`, `openhands`, `vecli`, `v0`). The whole value is matched first (VS Code's Copilot agent mode sets `AI_AGENT=github_copilot_vscode_agent`), then version suffixes are stripped, so `AI_AGENT=goose@1.2.3`, `AI_AGENT=v0@1.2.3`, and `AI_AGENT=claude-code_2-1-201_agent` all classify.
2. Tool-specific env vars:

   | Variable | Agent |
   |---|---|
   | `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_EXECPATH` | Claude Code |
   | `CLAUDE_CODE_IS_COWORK` (refines any Claude Code identification when present) | Claude Cowork |
   | `CODEBUDDY`, `CODEBUDDY_SESSION_ID`, `CODEBUDDY_PROJECT_DIR` (checked before Claude Code — CodeBuddy mirrors some `CLAUDE_*` vars) | CodeBuddy |
   | `CURSOR_AGENT` (set by both the CLI and the IDE's agent terminals) | Cursor |
   | `CURSOR_TRACE_ID` *and* `PAGER=head -n 10000 \| cat` (older builds; the PAGER override distinguishes agent mode from a human in Cursor's terminal) | Cursor |
   | `CURSOR_SANDBOX`, `CURSOR_EXTENSION_HOST_ROLE=agent-exec` | Cursor CLI |
   | `GEMINI_CLI` | Gemini CLI |
   | `QWEN_CODE` | Qwen Code |
   | `VECLI_SANDBOX`, `VECLI_DIR` (checked before `GEMINI_CLI` — veCLI is a Gemini CLI fork) | veCLI |
   | `CODEX_THREAD_ID`, `CODEX_SANDBOX`, `CODEX_SANDBOX_NETWORK_DISABLED`, `CODEX_CI` | OpenAI Codex |
   | `ANTIGRAVITY_AGENT`, `ANTIGRAVITY_PROJECT_ID` | Antigravity |
   | `AUGMENT_AGENT` | Augment |
   | `CLINE_ACTIVE`, `CLINE_TASK_ID` | Cline |
   | `ROO_CODE_TASK_ID` | Roo Code |
   | `CRUSH` | Crush |
   | `IFLOW_CLI` | iFlow CLI |
   | `GROK_AGENT` | Grok CLI |
   | `OZ_RUN_ID` | Warp |
   | `PI_CODING_AGENT`; nonblank `PI_SESSION_ID` as a fallback | Pi |
   | `KIRO_AGENT_PATH` | Kiro |
   | `AGENT_CONTEXT_OUT` *and* `AGENT_DISPLAY_OUT` (the Kiro CLI exports this FIFO pair only while its agent drives the command; either alone is too generic) | Kiro |
   | `FIREBENDER_TERMINAL` | Firebender |
   | `PS1` or `PROMPT_COMMAND` containing `###PS1JSON###` | OpenHands |
   | `DSH_SHELL=1` (exact) | DeepSeek Harness |
   | `KILO=1` (exact, before OpenCode) | Kilo Code |
   | `OPENCLAW_SHELL=exec` (exact) | OpenClaw |
   | `HERMES_AGENT=true` (exact), or generic `AI_AGENT=hermes-agent` | Hermes Agent |
   | `VTCODE=1` (exact) | VTCode |
   | `OPENCODE`, `OPENCODE_PID`, `OPENCODE_BIN_PATH`, `OPENCODE_SERVER`, `OPENCODE_APP_INFO`, `OPENCODE_MODES`, `OPENCODE_CLIENT` | OpenCode |
   | `TRAE_AI_SHELL_ID` | TRAE AI |
   | `GOOSE_TERMINAL` | Goose |
   | `REPL_ID` | Replit |
   | `AMP_CURRENT_THREAD_ID` | Amp |
   | `COPILOT_AGENT_SESSION_ID`, `COPILOT_AGENT`, `COPILOT_CLI`, `COPILOT_AGENT_JOB_ID`, `COPILOT_MODEL`, `COPILOT_ALLOW_ALL`, `COPILOT_GITHUB_TOKEN` | GitHub Copilot |
   | `AWS_EXECUTION_ENV` containing `AmazonQ-For-CLI` | Amazon Q Developer CLI |

   Ordering disambiguates compatibility shims and forks: Amp's and CodeBuddy's markers are checked before `CLAUDECODE` (Amp sets it for compat; CodeBuddy mirrors `CLAUDE_*` vars), and `QWEN_CODE`/`VECLI_*` before `GEMINI_CLI` (both are Gemini CLI forks that inherit `GEMINI_CLI=1`).

3. Filesystem signals:

   | Path | Agent |
   |---|---|
   | `/opt/.devin` | Devin |

4. A bare truthy `AGENT`/`AI_AGENT` (e.g. `AGENT=1`) as a last resort, resolving to `AgentId::Unknown`. Tool-specific vars outrank it, so agents that set both (e.g. OpenCode sets `AGENT=1` and `OPENCODE=1`) are still identified.

The detected `Agent` carries the `Signal` that matched, so callers can see exactly *how* detection fired.

## Real harness tests

A [container test lab](tests/harnesses/README.md) runs sixteen unmodified CLIs
against a Rust probe. Thirteen have detection assertions, including DeepSeek
Harness, Qwen Code, Kilo Code, OpenClaw, Hermes and VTCode. Goose and Cline remain
known detection gaps; Junie runs successfully but its candidate markers need
further controls before adding a rule. These are explicit discovery results,
not detection passes.

GitHub Actions runs the manifest on PRs, pushes to `main`, and before publishing
a release. A scripted local provider requests real shell-tool invocations;
no LLM credentials or vendor accounts are needed. The same tests run locally
with Docker or OrbStack. Reports retain versions, platform, source fingerprints,
identity and session checks, and correlated execution evidence.

The [discovery workflow](tests/harnesses/discovery.md) compares real tool
environments with controls, exporting reviewed safe values and redacting the rest. Trial version pins
and report comparisons make new releases and changed signals reviewable before
updating the detector. See the test lab README for commands and coverage limits.

PRs and releases test reviewed pins plus selected older compatibility versions.
A separate [Saturday watcher](.github/workflows/harness-watch.yml) resolves the
latest releases and compares fresh observations with each pin. It reports lost
detection, newly detectable agents, new candidate variable names, and execution
failures separately, retaining sanitized evidence for review.
The [environment inventory](tests/harnesses/inventory/README.md) is a generated
reference sheet of harnesses, variables and sanitized values, kept separately from detector rules. Weekly changes propose an
inventory-only PR; meaningful signal changes get a deduplicated investigation issue.

## License

Dual-licensed under MIT or Apache-2.0, at your option.
