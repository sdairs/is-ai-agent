# is-ai-agent

Detect whether a CLI is being invoked by an AI coding agent, and identify which one.

Inspired by the [`AGENT` environment variable proposal](https://github.com/agentsmd/agents.md/issues/136). Lets your CLI adapt its output — structured errors, more verbose tracebacks, no interactive prompts — when it's running under an agent rather than a human.

## Install

```toml
[dependencies]
is-ai-agent = "0.4"
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
    if let Some(session) = agent.session_id {
        eprintln!("session: {session}");
    }
}
```

### Session id

Many agentic CLIs expose a stable identifier for the current session/conversation to the subprocesses they spawn. `Agent::session_id` surfaces it as a single unified field, so a downstream tool can stamp it onto outbound requests (headers, query comments) and a backend can correlate every call that belongs to the same agent run.

The value is opaque and only comparable *within the same agent* — pair it with `agent.id` before correlating. It is `None` when the detected agent doesn't publish one.

| Agent | Source env var | Notes |
|---|---|---|
| Claude Code | `CLAUDE_CODE_SESSION_ID` | Per-conversation UUID; shared by sub-agents and all spawned subprocesses. |
| OpenAI Codex | `CODEX_THREAD_ID` | |
| Amp | `AMP_CURRENT_THREAD_ID`, then `AGENT_THREAD_ID` | |
| Qwen Code | `QWEN_CODE_SESSION_ID` | |
| Cursor / Cursor CLI | `CURSOR_TRACE_ID` | Trace id; per-session vs per-command scope is undocumented, so correlation may fragment. |
| GitHub Copilot | `COPILOT_AGENT_SESSION_ID` | |

Gemini CLI and Crush expose a session id only to *hooks*, not to ordinary subprocesses, so no id is available there.

For tests or callers that want to consult a captured environment instead of the live process, use `detect_with`:

```rust
use is_ai_agent::detect_with;

let agent = detect_with(
    |name| if name == "AGENT" { Some("goose".into()) } else { None },
    |_| false,
);
```

## Detection order

1. The generic `AGENT` (the [agents.md proposal](https://github.com/agentsmd/agents.md/issues/136)) and `AI_AGENT` ([@vercel/detect-agent](https://www.npmjs.com/package/@vercel/detect-agent)) env vars, when their value names a known agent (`goose`, `amp`, `claude-code`, `cursor`, `cursor-cli`, `gemini-cli`, `codex`, `augment`, `cline`, `opencode`, `trae`, `devin`, `replit`, `antigravity`, `github-copilot`, `crush`, `qwen-code`, `iflow-cli`, `amazon-q-cli`, `roo-code`). Version suffixes are stripped before matching, so `AI_AGENT=goose@1.2.3` and `AI_AGENT=claude-code_2.1.0_cli` both classify.
2. Tool-specific env vars:

   | Variable | Agent |
   |---|---|
   | `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_EXECPATH` | Claude Code |
   | `CURSOR_AGENT` (set by both the CLI and the IDE's agent terminals) | Cursor |
   | `CURSOR_TRACE_ID` *and* `PAGER=head -n 10000 \| cat` (older builds; the PAGER override distinguishes agent mode from a human in Cursor's terminal) | Cursor |
   | `CURSOR_SANDBOX`, `CURSOR_EXTENSION_HOST_ROLE=agent-exec` | Cursor CLI |
   | `GEMINI_CLI` | Gemini CLI |
   | `QWEN_CODE` | Qwen Code |
   | `CODEX_THREAD_ID`, `CODEX_SANDBOX`, `CODEX_SANDBOX_NETWORK_DISABLED`, `CODEX_CI` | OpenAI Codex |
   | `ANTIGRAVITY_AGENT` | Antigravity |
   | `AUGMENT_AGENT` | Augment |
   | `CLINE_ACTIVE` | Cline |
   | `ROO_ACTIVE` | Roo Code |
   | `CRUSH` | Crush |
   | `IFLOW_CLI` | iFlow CLI |
   | `OPENCODE`, `OPENCODE_PID`, `OPENCODE_CLIENT` | OpenCode |
   | `TRAE_AI_SHELL_ID` | TRAE AI |
   | `GOOSE_TERMINAL` | Goose |
   | `REPL_ID` | Replit |
   | `AMP_CURRENT_THREAD_ID` | Amp |
   | `COPILOT_AGENT_SESSION_ID`, `COPILOT_MODEL`, `COPILOT_ALLOW_ALL`, `COPILOT_GITHUB_TOKEN` | GitHub Copilot |
   | `AWS_EXECUTION_ENV` containing `AmazonQ-For-CLI` | Amazon Q Developer CLI |

   Ordering disambiguates compatibility shims: Amp's marker is checked before `CLAUDECODE` (Amp sets it for compat), and `QWEN_CODE` before `GEMINI_CLI` (Qwen Code is a Gemini CLI fork).

3. Filesystem signals:

   | Path | Agent |
   |---|---|
   | `/opt/.devin` | Devin |

4. A bare truthy `AGENT`/`AI_AGENT` (e.g. `AGENT=1`) as a last resort, resolving to `AgentId::Unknown`. Tool-specific vars outrank it, so agents that set both (e.g. OpenCode sets `AGENT=1` and `OPENCODE=1`) are still identified.

The detected `Agent` carries the `Signal` that matched, so callers can see exactly *how* detection fired.

## License

Dual-licensed under MIT or Apache-2.0, at your option.
