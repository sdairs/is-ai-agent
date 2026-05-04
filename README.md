# is-ai-agent

Detect whether a CLI is being invoked by an AI coding agent, and identify which one.

Inspired by the [`AGENT` environment variable proposal](https://github.com/agentsmd/agents.md/issues/136). Lets your CLI adapt its output — structured errors, more verbose tracebacks, no interactive prompts — when it's running under an agent rather than a human.

## Install

```toml
[dependencies]
is-ai-agent = "0.2"
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
}
```

For tests or callers that want to consult a captured environment instead of the live process, use `detect_with`:

```rust
use is_ai_agent::detect_with;

let agent = detect_with(
    |name| if name == "AGENT" { Some("goose".into()) } else { None },
    |_| false,
);
```

## Detection order

1. The proposed standard `AGENT` env var. Its value is mapped to a known agent (`goose`, `amp`, `claude-code`, `cursor`, `cursor-cli`, `gemini-cli`, `codex`, `augment`, `cline`, `opencode`, `trae`, `devin`, `replit`, `antigravity`, `github-copilot`); generic values like `1` / `true` resolve to `AgentId::Unknown`.
2. Tool-specific env vars:

   | Variable | Agent |
   |---|---|
   | `CLAUDECODE`, `CLAUDE_CODE` | Claude Code |
   | `CURSOR_TRACE_ID` | Cursor (editor) |
   | `CURSOR_AGENT`, `CURSOR_EXTENSION_HOST_ROLE=agent-exec` | Cursor CLI |
   | `GEMINI_CLI` | Gemini CLI |
   | `CODEX_SANDBOX`, `CODEX_CI`, `CODEX_THREAD_ID` | OpenAI Codex |
   | `ANTIGRAVITY_AGENT` | Antigravity |
   | `AUGMENT_AGENT` | Augment |
   | `CLINE_ACTIVE` | Cline |
   | `OPENCODE_CLIENT` | OpenCode |
   | `TRAE_AI_SHELL_ID` | TRAE AI |
   | `GOOSE_TERMINAL` | Goose |
   | `REPL_ID` | Replit |
   | `COPILOT_MODEL`, `COPILOT_ALLOW_ALL`, `COPILOT_GITHUB_TOKEN` | GitHub Copilot |

3. Filesystem signals:

   | Path | Agent |
   |---|---|
   | `/opt/.devin` | Devin |

The detected `Agent` carries the `Signal` that matched, so callers can see exactly *how* detection fired.

## License

Dual-licensed under MIT or Apache-2.0, at your option.
