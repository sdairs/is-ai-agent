# is-ai-agent

Detect whether a CLI is being invoked by an AI coding agent, and identify which one.

Inspired by the [`AGENT` environment variable proposal](https://github.com/agentsmd/agents.md/issues/136). Lets your CLI adapt its output — structured errors, more verbose tracebacks, no interactive prompts — when it's running under an agent rather than a human.

Detection provides cooperative attribution from environment variables and a small filesystem check. Inherited markers do not prove that a model initiated this particular command, and no match does not prove a human caller. It identifies the harness, not the model selected inside it.

## Install

```toml
[dependencies]
is-ai-agent = "0.5"
```

The detection refresh documented below is unreleased.

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
    // Opaque correlation id; its scope depends on the harness.
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

`Agent::session_id` surfaces a harness-provided correlation identifier. A downstream tool can attach it to outbound requests (headers, query comments), but session, thread, task and run identifiers have different lifetimes.

The value is opaque: pair it with `agent.id`, and account for the scope below before correlating. `None` means no supported identifier was available for the detected identity. Identity and metadata are read on every detection call; there is no cross-call session cache.

| Agent | Source env var | Notes |
|---|---|---|
| Claude Code / Claude Cowork | `CLAUDE_CODE_SESSION_ID` | Tool/hook children track `/clear`; long-lived MCP servers can retain their startup ID. See lifecycle notes below. |
| CodeBuddy | `CODEBUDDY_SESSION_ID`, then `CLAUDE_SESSION_ID` | Dual-written to a `CLAUDE_*` mirror. |
| OpenAI Codex | `CODEX_THREAD_ID` | Thread correlation only. `CODEX_SESSION_ID` identifies the shared root session and is not returned in this field. |
| Amp | `AMP_CURRENT_THREAD_ID`, then `AGENT_THREAD_ID` | |
| Qwen Code | `QWEN_CODE_SESSION_ID` | |
| Cursor / Cursor CLI | `CURSOR_TRACE_ID` | Trace id; per-session vs per-command scope is undocumented, so correlation may fragment. |
| GitHub Copilot | `COPILOT_AGENT_SESSION_ID`, then `COPILOT_AGENT_JOB_ID` | Job id is set by the Actions-based cloud coding agent. |
| Warp | `OZ_RUN_ID` | Run id; scope undocumented, so correlation may fragment. |
| Cline | `CLINE_TASK_ID` | |
| Roo Code | `ROO_CODE_TASK_ID` | |
| DeepSeek Harness | `DSH_SESSION_ID` | Nonblank, only after identity is established; the human web terminal also receives this variable. |
| Hermes Agent | `HERMES_SESSION_ID` | Nonblank session ID, not `HERMES_SESSION_THREAD_ID` messaging-thread routing metadata. |
| Grok Build | `GROK_SESSION_ID` | Nonblank; documented for tool commands and MCP servers since 1.0.4. |
| Pi | `PI_SESSION_ID` | Nonblank; injected into agent shell-tool commands, not human `!` / `!!` commands. |

New session sources reject whitespace-only values and preserve accepted values exactly. `DSH_PTY_SESSION_ID`, `KILO_RUN_ID`, `HERMES_SESSION_THREAD_ID` and trace context are not substitutes for these session IDs. Junie's observed `MATTERHORN_SESSION_ID` remains a research lead. There is no `GEMINI_CLI_SESSION_ID` or `OPENCODE_SESSION_ID` rule.

With only `CODEX_SESSION_ID`, detection returns Codex with `session_id=None`; when `CODEX_THREAD_ID` is also present, the thread ID is returned. `CODEX_VERSION` and `CODEX_PERMISSION_PROFILE` are metadata, not identity rules or permission guarantees. See the [Codex subprocess contract](https://github.com/openai/codex/blob/ec4d27ae8088e67785fb6d913462c8433f99dd47/codex-rs/core/src/exec_env.rs#L13).

For Claude, Bash/PowerShell tools and hooks receive the current conversation ID, including after `/clear`. A stdio MCP server keeps its spawn-time value; implicit resume/continue can leave it with a startup ID. Bridge/cloud IDs use different namespaces and are not substituted. The child marker covers tools, hooks and statusline commands, not stdio MCP servers; the broader `CLAUDECODE` marker can also appear in IDE terminals. See [Claude's environment reference](https://code.claude.com/docs/en/env-vars).

Pi's CLI/RPC identity markers and shell-tool session injection have different scope: SDK embedding does not automatically set the former, and human shell commands do not receive the latter. See the [Pi environment contract](https://github.com/earendil-works/pi/blob/fde38ed7c2f64434beffc6c0ec3b9994cb89ae23/packages/coding-agent/docs/environment-variables.md).

### Trace context

When the agent runs under [OpenTelemetry tracing](https://www.w3.org/TR/trace-context/), it may publish a `TRACEPARENT` to its subprocesses. `Agent::traceparent` exposes the raw W3C value (forward it as a `traceparent` header to keep downstream requests on the same distributed trace), and `Agent::trace_id()` extracts just the 32-hex trace-id correlation key.

`TRACEPARENT` is read after an identity matches; it is not itself an identity or session signal. It may be inherited from the ambient environment. Claude Code and Qwen Code both support propagation:

- Claude requires telemetry and enhanced tracing (`CLAUDE_CODE_ENABLE_TELEMETRY=1` and `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`). For a custom `ANTHROPIC_BASE_URL`, additionally set `CLAUDE_CODE_PROPAGATE_TRACEPARENT=1`; the direct Anthropic route does not require that extra flag. See [Claude tracing](https://code.claude.com/docs/en/monitoring-usage#traces-beta).
- Qwen Code gates propagation on telemetry and `outboundCorrelation.propagateTraceContext`. Its [shell context](https://github.com/QwenLM/qwen-code/blob/94104d5565b1d45de3d5e724215410fa26582ec7/packages/core/src/services/shellContextEnv.ts#L115) is prepared per session. A trace ID must not be treated as a conversation ID.

For tests or callers that want to consult a captured environment instead of the live process, use `detect_with`:

```rust
use is_ai_agent::detect_with;

let agent = detect_with(
    |name| if name == "AGENT" { Some("goose".into()) } else { None },
    |_| false,
);
```

## Detection order

1. The generic `AGENT` (the [agents.md proposal](https://github.com/agentsmd/agents.md/issues/136)) and then `AI_AGENT` ([@vercel/detect-agent](https://www.npmjs.com/package/@vercel/detect-agent)) env vars, when their value names a known agent. Existing canonical slugs are `goose`, `amp`, `claude-code`, `cowork`, `cursor`, `cursor-cli`, `gemini-cli`, `codex`, `augment`, `cline`, `opencode`, `trae`, `devin`, `replit`, `antigravity`, `github-copilot`, `crush`, `qwen-code`, `iflow-cli`, `amazon-q-cli`, `roo-code`, `codebuddy`, `grok-cli`, `warp`, `pi`, `kiro`, `firebender`, `openhands`, `vecli`, and `v0`; the seven new slugs and aliases are below. Generic aliases are explicit caller assertions, not claims that vendors export every spelling. A known outer identity wins over an inner harness marker. Whole-name matching comes before existing `@version` / underscore suffix handling, so `github_copilot_vscode_agent`, the new `github_copilot_app_agent`, `goose@1.2.3`, and `claude-code_2-1-201_agent` classify correctly.

   Blank/whitespace-only values and trimmed `0`, `false`, `no`, or `off` (case-insensitive) are ignored. They do not disable other detection: `AGENT=false` with `KILO=1` still identifies Kilo Code.
2. Tool-specific env vars:

   New rules use the exact predicates below. **Exact** means case-sensitive, without trimming; **nonblank** rejects whitespace-only values and preserves the original matched value.

   | Variant / display name | Canonical slug; extra generic aliases | Automatic detection | Evidence / scope |
   |---|---|---|---|
   | `DeepSeekHarness` / DeepSeek Harness | `deepseek-harness`; `dsh` | Exact `DSH_SHELL=1` | [Shell registry](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/shell/shell-env/src/index.ts#L156), [agent PTY](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/terminal/terminal-bash/src/index.ts#L64); inspected model tools and persistent terminal backend. |
   | `Hermes` / Hermes Agent | `hermes-agent`; `hermes` | Exact `HERMES_AGENT=true`, then nonblank `HERMES_SESSION_ID` fallback | [Subprocess contract](https://github.com/NousResearch/hermes-agent/blob/07646a7f72773e08197ac138295fba8f317973d2/website/docs/reference/environment-variables.md#L899). |
   | `OpenClaw` / OpenClaw | `openclaw` | Exact `OPENCLAW_SHELL=exec` | [Exec contract](https://github.com/openclaw/openclaw/blob/bab3136d3c6074faf0c91c409619969749885b7e/docs/tools/exec.md#L82); `tui-local`, `acp-client`, `acp` and other values do not match. |
   | `GrokBuild` / Grok Build | `grok-build` | Nonblank `GROK_SESSION_ID` | [1.0.4 changelog](https://x.ai/build/changelog), tool commands and MCP servers. Separate from legacy Grok CLI and Grok Bot. |
   | `KiloCode` / Kilo Code | `kilo-code`; `kilo`, `kilocode` | Exact `KILO=1`, before OpenCode | [CLI setup](https://github.com/Kilo-Org/kilocode/blob/640786b363b6f8b27d4e2ef5ad29dd014dae7c3c/packages/opencode/src/kilocode/cli/setup.ts#L82); inspected CLI, not every IDE surface. |
   | `Junie` / Junie | `junie` | Nonblank `JUNIE_SHIM_PATH` | [Official launcher](https://github.com/JetBrains/junie/blob/a3765b65ff98812ed33244bd242193146d2ea847/templates/junie.shim.sh#L696); shim-launched ancestry, without a human-command distinction. No `JUNIE_DATA` fallback. |
   | `VTCode` / VTCode | `vtcode` | Exact `VTCODE=1` | [Bootstrap](https://github.com/vinhnx/VTCode/blob/edad07882a01de96f116e949bd1cf611e020d449/src/main.rs#L149). |

   Existing identities gain exact `CLAUDE_CODE_CHILD_SESSION=1` before broader Claude markers, nonblank `CODEX_SESSION_ID` as a Codex fallback, and nonblank `PI_SESSION_ID` as a Pi fallback. Other retained rules are listed below. Unless a predicate is written explicitly, these legacy rules accept any nonempty value; this refresh does not certify or tighten every legacy rule.

   | Variable | Agent |
   |---|---|
   | `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_EXECPATH` | Claude Code |
   | `CLAUDE_CODE_IS_COWORK` (refines any Claude Code identification when nonempty) | Claude Cowork |
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
   | `OZ_RUN_ID` | Warp |
   | `PI_CODING_AGENT` | Pi |
   | `KIRO_AGENT_PATH` | Kiro |
   | `AGENT_CONTEXT_OUT` *and* `AGENT_DISPLAY_OUT` (the Kiro CLI exports this FIFO pair only while its agent drives the command; either alone is too generic) | Kiro |
   | `FIREBENDER_TERMINAL` | Firebender |
   | `PS1` or `PROMPT_COMMAND` containing `###PS1JSON###` | OpenHands |
   | `OPENCODE`, `OPENCODE_PID`, `OPENCODE_BIN_PATH`, `OPENCODE_SERVER`, `OPENCODE_APP_INFO`, `OPENCODE_MODES`, `OPENCODE_CLIENT` | OpenCode |
   | `TRAE_AI_SHELL_ID` | TRAE AI |
   | `GOOSE_TERMINAL` | Goose |
   | `AMP_CURRENT_THREAD_ID` | Amp |
   | `COPILOT_AGENT_SESSION_ID`, `COPILOT_AGENT`, `COPILOT_CLI`, `COPILOT_AGENT_JOB_ID` | GitHub Copilot |
   | `AWS_EXECUTION_ENV` containing `AmazonQ-For-CLI` | Amazon Q Developer CLI |

   Ordering disambiguates compatibility shims and forks: Amp and CodeBuddy precede Claude, Cowork refinement is preserved, Qwen Code and veCLI precede Gemini CLI, and Kilo precedes OpenCode. Known generic names still win over these markers; bare generic true values do not.

3. Filesystem signals:

   | Path | Agent |
   |---|---|
   | `/opt/.devin` | Devin |

4. An unknown nonblank generic name or bare true value (e.g. `AGENT=1`) as a last resort, resolving to `AgentId::Unknown`. Tool-specific and filesystem signals outrank it, so `AGENT=1`, `KILO=1`, and `OPENCODE=1` together identify Kilo Code.

The detected `Agent` carries the `Signal` that matched, so callers can see exactly *how* detection fired.

### Intentional exclusions

`COPILOT_GITHUB_TOKEN`, `COPILOT_MODEL`, `COPILOT_ALLOW_ALL`, bare `REPL_ID`, and bare `GROK_AGENT` no longer trigger detection. Credentials, configuration and a workspace ID are insufficient; matching a token also copied it into the public/debug result. [`GROK_AGENT` is a profile selector](https://docs.x.ai/build/settings/reference#environment-variables). `GrokCli` and Replit remain available through their existing generic aliases (`grok` / `grok-cli` and `replit`). No `REPLIT_MODE` replacement is added.

`DSH_SESSION_ID` alone is insufficient because the [human web terminal also receives it](https://github.com/deepseek-ai/deepseek-harness/blob/00102833dfaee1da9f48a3a8eae9d34005a75218/packages/api/terminal-controller/src/index.ts#L346). `DEEPSEEK_API_KEY`, `DSH_HOME`, `DSH_PROFILE`, and `DSH_PROFILE_DIR` are not identity rules. The inspected DeepSeek tools supply fresh tool-owned values; arbitrary plugin propagation is not assumed. Selecting a DeepSeek or Qwen model in another harness does not identify that harness as DeepSeek Harness or Qwen Code.

Qwen Live Harness delegates to other coding harnesses. Its settings and `QWEN_CODE_NO_RELAUNCH` do not establish Qwen Code execution or a separate Qwen Live identity; the underlying executor is identified when its own marker is present. No new model, version, root-session, confidence, or multi-match fields are added.

### Evidence and remaining gaps

The [captured inventory](tests/harnesses/inventory/observed.json) records exact environments from real command tools using a scripted provider. The [harness README](tests/harnesses/README.md) explains how to replay it against the detector; the [discovery report](tests/harnesses/discovery.md) explains pinned versions, controls and limits. Six new identities were observed there: DeepSeek Harness, Hermes Agent, OpenClaw, Kilo Code, Junie and VTCode. Grok Build is supported from vendor documentation, without a live probe in this inventory. Source inspection and those controlled runs do not establish every installed version, operating system, IDE, human-command, nested or resumed-session path.

Cline CLI's observed wrapper/connector variables also appear in a non-agent command control. Goose 1.52.0 exposes generic `AGENT_SESSION_ID`, while its provider/model variables are inherited configuration. Those observations do not justify new identity rules; both detection gaps remain. Junie's shim path identifies launcher ancestry, and the attempted interactive human-command control was inconclusive. The retained legacy rules remain subject to separate evidence review, as recorded in [issue #5](https://github.com/sdairs/is-ai-agent/issues/5).

## License

Dual-licensed under MIT or Apache-2.0, at your option.
