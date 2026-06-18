//! Detect whether the current process is being invoked by an AI coding agent,
//! and identify which one.
//!
//! Detection order:
//! 1. The generic `AGENT` (agentsmd/agents.md#136) and `AI_AGENT`
//!    (@vercel/detect-agent) env vars, when their value names a known agent.
//! 2. Tool-specific env vars (`CLAUDECODE`, `CURSOR_AGENT`, ...).
//! 3. Filesystem signals (e.g. `/opt/.devin`).
//! 4. A bare truthy `AGENT`/`AI_AGENT` (e.g. `AGENT=1`) as a last resort,
//!    resolving to [`AgentId::Unknown`]. Tool-specific vars outrank it so
//!    agents that set both (e.g. OpenCode sets `AGENT=1` and `OPENCODE=1`)
//!    are still identified.
//!
//! ```no_run
//! if is_ai_agent::is_ai_agent() {
//!     // emit structured output
//! }
//!
//! if let Some(agent) = is_ai_agent::detect() {
//!     eprintln!("running under {}", agent.name);
//! }
//! ```

use std::env;
use std::path::Path;

/// A detected AI agent and the signal that revealed it.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub struct Agent {
    pub id: AgentId,
    pub name: &'static str,
    pub signal: Signal,
    /// A stable identifier for the agent's current session/conversation, when
    /// the agent exposes one to its subprocesses via an env var.
    ///
    /// The vendors call this variously a session, thread, or trace id; here it
    /// is unified as "the identifier that correlates every tool invocation in
    /// one agent run". It is opaque and only comparable within the same agent
    /// — pair it with [`AgentId`] before correlating across surfaces. `None`
    /// when the detected agent doesn't publish one (e.g. Gemini CLI and Crush
    /// only expose it to hooks, not to ordinary subprocesses).
    pub session_id: Option<String>,
    /// The active [W3C Trace Context] `traceparent` value, when present in the
    /// environment — the raw header a subprocess can forward to keep
    /// downstream requests on the same distributed trace.
    ///
    /// Of the agents covered here, Claude Code and Qwen Code propagate this
    /// (both gated behind telemetry being enabled, and off by default).
    /// Others may surface a `traceparent` only if one was already present in
    /// the ambient shell and inherited. Use [`Agent::trace_id`] for just the
    /// trace-id correlation key.
    ///
    /// [W3C Trace Context]: https://www.w3.org/TR/trace-context/#traceparent-header
    pub traceparent: Option<String>,
}

impl Agent {
    /// The 32-hex-digit trace-id extracted from [`Agent::traceparent`], i.e.
    /// the correlation key shared by every span in the trace. `None` when no
    /// `traceparent` is present or it isn't a well-formed W3C value.
    pub fn trace_id(&self) -> Option<&str> {
        // traceparent = version "-" trace-id "-" parent-id "-" flags
        let mut parts = self.traceparent.as_deref()?.split('-');
        let _version = parts.next()?;
        let trace_id = parts.next()?;
        // A valid trace-id is 32 lowercase hex digits and not all-zero.
        let valid = trace_id.len() == 32
            && trace_id.bytes().all(|b| b.is_ascii_hexdigit())
            && trace_id.bytes().any(|b| b != b'0');
        valid.then_some(trace_id)
    }
}

/// Canonical identifier for a known agent, or `Unknown` when an agent is
/// present but its specific identity can't be determined (e.g. `AGENT=1`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
#[non_exhaustive]
pub enum AgentId {
    ClaudeCode,
    Cursor,
    CursorCli,
    GeminiCli,
    Codex,
    Augment,
    Cline,
    OpenCode,
    Trae,
    Goose,
    Amp,
    Devin,
    Replit,
    Antigravity,
    GitHubCopilot,
    Crush,
    QwenCode,
    IflowCli,
    AmazonQCli,
    RooCode,
    Unknown,
}

impl AgentId {
    /// A stable, URL-safe lowercase slug for this agent.
    ///
    /// These slugs round-trip through the `AGENT` env var convention:
    /// setting `AGENT=<slug>` will be classified back to the same `AgentId`.
    pub fn as_str(&self) -> &'static str {
        match self {
            AgentId::ClaudeCode => "claude-code",
            AgentId::Cursor => "cursor",
            AgentId::CursorCli => "cursor-cli",
            AgentId::GeminiCli => "gemini-cli",
            AgentId::Codex => "codex",
            AgentId::Augment => "augment",
            AgentId::Cline => "cline",
            AgentId::OpenCode => "opencode",
            AgentId::Trae => "trae",
            AgentId::Goose => "goose",
            AgentId::Amp => "amp",
            AgentId::Devin => "devin",
            AgentId::Replit => "replit",
            AgentId::Antigravity => "antigravity",
            AgentId::GitHubCopilot => "github-copilot",
            AgentId::Crush => "crush",
            AgentId::QwenCode => "qwen-code",
            AgentId::IflowCli => "iflow-cli",
            AgentId::AmazonQCli => "amazon-q-cli",
            AgentId::RooCode => "roo-code",
            AgentId::Unknown => "unknown",
        }
    }
}

/// What signal triggered the detection.
#[derive(Debug, Clone, PartialEq, Eq)]
#[non_exhaustive]
pub enum Signal {
    EnvVar { name: &'static str, value: String },
    File { path: &'static str },
}

const TOOL_VARS: &[(&str, AgentId, &str)] = &[
    // Amp sets CLAUDECODE=1 for compatibility, so its own marker must be
    // checked before Claude Code's.
    ("AMP_CURRENT_THREAD_ID", AgentId::Amp, "Amp"),
    ("CLAUDECODE", AgentId::ClaudeCode, "Claude Code"),
    ("CLAUDE_CODE_ENTRYPOINT", AgentId::ClaudeCode, "Claude Code"),
    ("CLAUDE_CODE_SESSION_ID", AgentId::ClaudeCode, "Claude Code"),
    ("CLAUDE_CODE_EXECPATH", AgentId::ClaudeCode, "Claude Code"),
    // Set by both the Cursor CLI and the IDE's agent terminals, so it only
    // proves "some Cursor agent surface", not specifically the CLI.
    ("CURSOR_AGENT", AgentId::Cursor, "Cursor"),
    ("CURSOR_SANDBOX", AgentId::CursorCli, "Cursor CLI"),
    // Qwen Code is a Gemini CLI fork; its marker must precede Gemini's.
    ("QWEN_CODE", AgentId::QwenCode, "Qwen Code"),
    ("GEMINI_CLI", AgentId::GeminiCli, "Gemini CLI"),
    ("CODEX_THREAD_ID", AgentId::Codex, "OpenAI Codex"),
    ("CODEX_SANDBOX", AgentId::Codex, "OpenAI Codex"),
    (
        "CODEX_SANDBOX_NETWORK_DISABLED",
        AgentId::Codex,
        "OpenAI Codex",
    ),
    ("CODEX_CI", AgentId::Codex, "OpenAI Codex"),
    ("ANTIGRAVITY_AGENT", AgentId::Antigravity, "Antigravity"),
    ("AUGMENT_AGENT", AgentId::Augment, "Augment"),
    ("CLINE_ACTIVE", AgentId::Cline, "Cline"),
    ("ROO_ACTIVE", AgentId::RooCode, "Roo Code"),
    ("CRUSH", AgentId::Crush, "Crush"),
    ("IFLOW_CLI", AgentId::IflowCli, "iFlow CLI"),
    ("OPENCODE", AgentId::OpenCode, "OpenCode"),
    ("OPENCODE_PID", AgentId::OpenCode, "OpenCode"),
    // No longer set in plain CLI/TUI use (only acp/desktop embeddings).
    ("OPENCODE_CLIENT", AgentId::OpenCode, "OpenCode"),
    ("TRAE_AI_SHELL_ID", AgentId::Trae, "TRAE AI"),
    ("GOOSE_TERMINAL", AgentId::Goose, "Goose"),
    ("REPL_ID", AgentId::Replit, "Replit"),
    (
        "COPILOT_AGENT_SESSION_ID",
        AgentId::GitHubCopilot,
        "GitHub Copilot",
    ),
    // Inherited user config rather than injected markers — weaker signals.
    ("COPILOT_MODEL", AgentId::GitHubCopilot, "GitHub Copilot"),
    (
        "COPILOT_ALLOW_ALL",
        AgentId::GitHubCopilot,
        "GitHub Copilot",
    ),
    (
        "COPILOT_GITHUB_TOKEN",
        AgentId::GitHubCopilot,
        "GitHub Copilot",
    ),
];

const FILE_SIGNALS: &[(&str, AgentId, &str)] = &[("/opt/.devin", AgentId::Devin, "Devin")];

/// Per-agent env vars that carry a session/thread/trace identifier reachable
/// from spawned subprocesses, in priority order. Only agents that publish such
/// an id to ordinary subprocesses appear here.
const SESSION_ID_VARS: &[(AgentId, &[&str])] = &[
    (AgentId::ClaudeCode, &["CLAUDE_CODE_SESSION_ID"]),
    (AgentId::Codex, &["CODEX_THREAD_ID"]),
    // Amp sets both to the same thread id; AGENT_THREAD_ID is the fallback.
    (AgentId::Amp, &["AMP_CURRENT_THREAD_ID", "AGENT_THREAD_ID"]),
    (AgentId::QwenCode, &["QWEN_CODE_SESSION_ID"]),
    // Cursor exposes only a trace id; its per-session vs per-command scope is
    // undocumented, so callers correlating on it should expect possible churn.
    (AgentId::Cursor, &["CURSOR_TRACE_ID"]),
    (AgentId::CursorCli, &["CURSOR_TRACE_ID"]),
    (AgentId::GitHubCopilot, &["COPILOT_AGENT_SESSION_ID"]),
];

/// Returns `true` if any AI agent signal is present.
pub fn is_ai_agent() -> bool {
    detect().is_some()
}

/// Detect the AI agent, if any.
pub fn detect() -> Option<Agent> {
    detect_with(|name| env::var(name).ok(), |path| Path::new(path).exists())
}

/// Detection with injectable lookups, useful for tests and for callers that
/// want to consult a captured environment instead of the live process.
pub fn detect_with<E, F>(env: E, file_exists: F) -> Option<Agent>
where
    E: Fn(&str) -> Option<String>,
    F: Fn(&str) -> bool,
{
    // Builds the result, resolving the agent's session id and the active W3C
    // trace context from the same environment so every construction site stays
    // consistent. `traceparent` is a standard var name (not agent-specific),
    // so it is read directly rather than via a per-agent table.
    let make = |id: AgentId, name: &'static str, signal: Signal| Agent {
        id,
        name,
        signal,
        session_id: session_id_for(id, &env),
        traceparent: nonempty(env("TRACEPARENT")),
    };

    // Generic vars win outright when they name a known agent. A bare truthy
    // value (`AGENT=1`) only proves *an* agent is present, so it is held as
    // a fallback while the more specific signals below get a chance to
    // identify the tool — e.g. OpenCode sets both AGENT=1 and OPENCODE=1.
    let mut generic_fallback = None;
    for var in ["AGENT", "AI_AGENT"] {
        if let Some(value) = nonempty(env(var)) {
            let (id, name) = classify_agent_value(agent_name_part(&value));
            let agent = make(id, name, Signal::EnvVar { name: var, value });
            if id != AgentId::Unknown {
                return Some(agent);
            }
            if generic_fallback.is_none() {
                generic_fallback = Some(agent);
            }
        }
    }

    // Special-cased value match: Cursor's extension host signals an agent
    // execution context only when the value equals "agent-exec".
    if let Some(value) = nonempty(env("CURSOR_EXTENSION_HOST_ROLE"))
        && value.trim() == "agent-exec"
    {
        return Some(make(
            AgentId::CursorCli,
            "Cursor CLI",
            Signal::EnvVar {
                name: "CURSOR_EXTENSION_HOST_ROLE",
                value,
            },
        ));
    }

    // Special-cased combination match: older Cursor builds (pre ~v3.7) set
    // CURSOR_TRACE_ID in every integrated terminal, including interactive
    // human sessions. Agent mode is distinguished by the PAGER override
    // Cursor applies when running commands itself.
    if let Some(value) = nonempty(env("CURSOR_TRACE_ID"))
        && env("PAGER").as_deref() == Some("head -n 10000 | cat")
    {
        return Some(make(
            AgentId::Cursor,
            "Cursor",
            Signal::EnvVar {
                name: "CURSOR_TRACE_ID",
                value,
            },
        ));
    }

    // Special-cased substring match: Amazon Q Developer CLI appends itself
    // to AWS_EXECUTION_ENV (e.g. "AmazonQ-For-CLI Version/1.16.0"), a var
    // that other AWS runtimes also set.
    if let Some(value) = nonempty(env("AWS_EXECUTION_ENV"))
        && value.contains("AmazonQ-For-CLI")
    {
        return Some(make(
            AgentId::AmazonQCli,
            "Amazon Q Developer CLI",
            Signal::EnvVar {
                name: "AWS_EXECUTION_ENV",
                value,
            },
        ));
    }

    for &(var, id, name) in TOOL_VARS {
        if let Some(value) = nonempty(env(var)) {
            return Some(make(id, name, Signal::EnvVar { name: var, value }));
        }
    }

    for &(path, id, name) in FILE_SIGNALS {
        if file_exists(path) {
            return Some(make(id, name, Signal::File { path }));
        }
    }

    generic_fallback
}

/// Resolve the session/thread/trace id the given agent exposes via env vars,
/// trying each candidate var in priority order.
fn session_id_for<E>(id: AgentId, env: &E) -> Option<String>
where
    E: Fn(&str) -> Option<String>,
{
    let vars = SESSION_ID_VARS
        .iter()
        .find(|(agent, _)| *agent == id)
        .map(|(_, vars)| *vars)?;
    vars.iter().find_map(|var| nonempty(env(var)))
}

fn nonempty(v: Option<String>) -> Option<String> {
    v.filter(|s| !s.is_empty())
}

/// Extract the agent name from a generic var value. Strips the version
/// suffixes in the wild: `name@version` (Vercel's @vercel/detect-agent
/// convention, e.g. `v0@1.2.3`) and `name_version_surface` (Claude Code's
/// AI_AGENT shape, e.g. `claude-code_2.1.0_cli`).
fn agent_name_part(value: &str) -> &str {
    let name = value.trim();
    let name = name.split('@').next().unwrap_or(name);
    name.split('_').next().unwrap_or(name)
}

fn classify_agent_value(value: &str) -> (AgentId, &'static str) {
    match value.trim().to_ascii_lowercase().as_str() {
        "goose" => (AgentId::Goose, "Goose"),
        "amp" => (AgentId::Amp, "Amp"),
        "claude" | "claude-code" | "claudecode" => (AgentId::ClaudeCode, "Claude Code"),
        "cursor" => (AgentId::Cursor, "Cursor"),
        "cursor-cli" => (AgentId::CursorCli, "Cursor CLI"),
        "gemini" | "gemini-cli" => (AgentId::GeminiCli, "Gemini CLI"),
        "codex" => (AgentId::Codex, "OpenAI Codex"),
        "augment" | "augment-cli" => (AgentId::Augment, "Augment"),
        "cline" => (AgentId::Cline, "Cline"),
        "opencode" => (AgentId::OpenCode, "OpenCode"),
        "trae" => (AgentId::Trae, "TRAE AI"),
        "devin" => (AgentId::Devin, "Devin"),
        "replit" => (AgentId::Replit, "Replit"),
        "antigravity" => (AgentId::Antigravity, "Antigravity"),
        "github-copilot" | "github-copilot-cli" => (AgentId::GitHubCopilot, "GitHub Copilot"),
        "crush" => (AgentId::Crush, "Crush"),
        "qwen" | "qwen-code" | "qwencode" => (AgentId::QwenCode, "Qwen Code"),
        "iflow" | "iflow-cli" => (AgentId::IflowCli, "iFlow CLI"),
        "amazonq" | "amazon-q" | "amazon-q-cli" => (AgentId::AmazonQCli, "Amazon Q Developer CLI"),
        "roo" | "roo-code" | "roocode" => (AgentId::RooCode, "Roo Code"),
        _ => (AgentId::Unknown, "AI agent"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    fn env_from(pairs: &[(&str, &str)]) -> impl Fn(&str) -> Option<String> + use<> {
        let map: HashMap<String, String> = pairs
            .iter()
            .map(|(k, v)| ((*k).to_string(), (*v).to_string()))
            .collect();
        move |name| map.get(name).cloned()
    }

    #[test]
    fn returns_none_when_nothing_set() {
        let env = env_from(&[]);
        assert!(detect_with(env, |_| false).is_none());
    }

    #[test]
    fn agent_var_with_known_name_classifies() {
        let env = env_from(&[("AGENT", "goose")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::Goose);
        assert_eq!(
            agent.signal,
            Signal::EnvVar {
                name: "AGENT",
                value: "goose".to_string()
            }
        );
    }

    #[test]
    fn agent_var_normalizes_case_and_aliases() {
        let env = env_from(&[("AGENT", "Claude-Code")]);
        assert_eq!(detect_with(env, |_| false).unwrap().id, AgentId::ClaudeCode);
    }

    #[test]
    fn agent_var_with_truthy_value_is_unknown() {
        let env = env_from(&[("AGENT", "1")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::Unknown);
        assert_eq!(agent.name, "AI agent");
    }

    #[test]
    fn agent_var_takes_priority_over_tool_var() {
        let env = env_from(&[("AGENT", "amp"), ("CLAUDECODE", "1")]);
        assert_eq!(detect_with(env, |_| false).unwrap().id, AgentId::Amp);
    }

    #[test]
    fn tool_var_falls_back_when_agent_unset() {
        let env = env_from(&[("CURSOR_AGENT", "1")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::Cursor);
        assert_eq!(
            agent.signal,
            Signal::EnvVar {
                name: "CURSOR_AGENT",
                value: "1".to_string()
            }
        );
    }

    #[test]
    fn empty_var_value_is_ignored() {
        let env = env_from(&[("AGENT", ""), ("CLAUDECODE", "1")]);
        assert_eq!(detect_with(env, |_| false).unwrap().id, AgentId::ClaudeCode);
    }

    #[test]
    fn devin_marker_file_detected() {
        let env = env_from(&[]);
        let agent = detect_with(env, |p| p == "/opt/.devin").unwrap();
        assert_eq!(agent.id, AgentId::Devin);
        assert_eq!(
            agent.signal,
            Signal::File {
                path: "/opt/.devin"
            }
        );
    }

    #[test]
    fn env_vars_take_priority_over_files() {
        let env = env_from(&[("CLAUDECODE", "1")]);
        assert_eq!(detect_with(env, |_| true).unwrap().id, AgentId::ClaudeCode);
    }

    #[test]
    fn claude_code_sibling_vars_detected() {
        for var in [
            "CLAUDE_CODE_ENTRYPOINT",
            "CLAUDE_CODE_SESSION_ID",
            "CLAUDE_CODE_EXECPATH",
        ] {
            let env = env_from(&[(var, "x")]);
            let agent = detect_with(env, |_| false).unwrap();
            assert_eq!(agent.id, AgentId::ClaudeCode, "var={var}");
        }
    }

    #[test]
    fn ai_agent_var_with_known_name_classifies() {
        let env = env_from(&[("AI_AGENT", "crush")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::Crush);
        assert_eq!(
            agent.signal,
            Signal::EnvVar {
                name: "AI_AGENT",
                value: "crush".to_string()
            }
        );
    }

    #[test]
    fn ai_agent_var_strips_version_suffixes() {
        // Claude Code's shape: name_version_surface.
        let env = env_from(&[("AI_AGENT", "claude-code_2.1.0_cli")]);
        assert_eq!(detect_with(env, |_| false).unwrap().id, AgentId::ClaudeCode);

        // Vercel's @vercel/detect-agent shape: name@version.
        let env = env_from(&[("AI_AGENT", "goose@1.2.3")]);
        assert_eq!(detect_with(env, |_| false).unwrap().id, AgentId::Goose);
    }

    #[test]
    fn truthy_agent_var_defers_to_tool_vars() {
        // OpenCode sets AGENT=1 alongside its own markers; the specific
        // marker must win over the generic truthy value.
        let env = env_from(&[("AGENT", "1"), ("OPENCODE", "1")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::OpenCode);
        assert_eq!(
            agent.signal,
            Signal::EnvVar {
                name: "OPENCODE",
                value: "1".to_string()
            }
        );
    }

    #[test]
    fn truthy_agent_var_defers_to_file_signals() {
        let env = env_from(&[("AGENT", "true")]);
        let agent = detect_with(env, |p| p == "/opt/.devin").unwrap();
        assert_eq!(agent.id, AgentId::Devin);
    }

    #[test]
    fn truthy_ai_agent_var_is_unknown_fallback() {
        let env = env_from(&[("AI_AGENT", "1")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::Unknown);
        assert_eq!(
            agent.signal,
            Signal::EnvVar {
                name: "AI_AGENT",
                value: "1".to_string()
            }
        );
    }

    #[test]
    fn amp_marker_outranks_claudecode_compat_var() {
        // Amp sets CLAUDECODE=1 for compatibility.
        let env = env_from(&[("AMP_CURRENT_THREAD_ID", "t-1"), ("CLAUDECODE", "1")]);
        assert_eq!(detect_with(env, |_| false).unwrap().id, AgentId::Amp);
    }

    #[test]
    fn qwen_code_outranks_gemini_cli_var() {
        // Qwen Code is a Gemini CLI fork.
        let env = env_from(&[("QWEN_CODE", "1"), ("GEMINI_CLI", "1")]);
        assert_eq!(detect_with(env, |_| false).unwrap().id, AgentId::QwenCode);
    }

    #[test]
    fn new_tool_vars_detected() {
        for (var, expected) in [
            ("CRUSH", AgentId::Crush),
            ("QWEN_CODE", AgentId::QwenCode),
            ("IFLOW_CLI", AgentId::IflowCli),
            ("ROO_ACTIVE", AgentId::RooCode),
            ("OPENCODE", AgentId::OpenCode),
            ("OPENCODE_PID", AgentId::OpenCode),
            ("CURSOR_SANDBOX", AgentId::CursorCli),
            ("CODEX_SANDBOX_NETWORK_DISABLED", AgentId::Codex),
            ("AMP_CURRENT_THREAD_ID", AgentId::Amp),
            ("COPILOT_AGENT_SESSION_ID", AgentId::GitHubCopilot),
        ] {
            let env = env_from(&[(var, "1")]);
            let agent = detect_with(env, |_| false).unwrap();
            assert_eq!(agent.id, expected, "var={var}");
        }
    }

    #[test]
    fn amazon_q_detected_via_aws_execution_env_substring() {
        let env = env_from(&[("AWS_EXECUTION_ENV", "AmazonQ-For-CLI Version/1.16.0")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::AmazonQCli);
    }

    #[test]
    fn aws_execution_env_without_amazon_q_ignored() {
        let env = env_from(&[("AWS_EXECUTION_ENV", "AWS_Lambda_nodejs22.x")]);
        assert!(detect_with(env, |_| false).is_none());
    }

    #[test]
    fn cursor_trace_id_with_pager_override_detected() {
        let env = env_from(&[
            ("CURSOR_TRACE_ID", "abc123"),
            ("PAGER", "head -n 10000 | cat"),
        ]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::Cursor);
        assert_eq!(
            agent.signal,
            Signal::EnvVar {
                name: "CURSOR_TRACE_ID",
                value: "abc123".to_string()
            }
        );
    }

    #[test]
    fn cursor_trace_id_alone_is_interactive_not_agent() {
        // Older Cursor builds set CURSOR_TRACE_ID for human terminal
        // sessions too; without the agent-mode PAGER override it must not
        // count as an agent.
        let env = env_from(&[("CURSOR_TRACE_ID", "abc123")]);
        assert!(detect_with(env, |_| false).is_none());
    }

    #[test]
    fn cursor_agent_var_maps_to_generic_cursor() {
        // CURSOR_AGENT is set by both the CLI and the IDE's agent terminals.
        let env = env_from(&[("CURSOR_AGENT", "1")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::Cursor);
        assert_eq!(agent.name, "Cursor");
    }

    #[test]
    fn cursor_cli_detected_via_extension_host_role() {
        let env = env_from(&[("CURSOR_EXTENSION_HOST_ROLE", "agent-exec")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::CursorCli);
    }

    #[test]
    fn cursor_extension_host_role_other_value_ignored() {
        let env = env_from(&[("CURSOR_EXTENSION_HOST_ROLE", "ui")]);
        assert!(detect_with(env, |_| false).is_none());
    }

    #[test]
    fn codex_alternate_signals_detected() {
        for var in ["CODEX_SANDBOX", "CODEX_CI", "CODEX_THREAD_ID"] {
            let env = env_from(&[(var, "1")]);
            let agent = detect_with(env, |_| false).unwrap();
            assert_eq!(agent.id, AgentId::Codex, "var={var}");
        }
    }

    #[test]
    fn antigravity_detected() {
        let env = env_from(&[("ANTIGRAVITY_AGENT", "1")]);
        assert_eq!(
            detect_with(env, |_| false).unwrap().id,
            AgentId::Antigravity
        );
    }

    #[test]
    fn replit_detected() {
        let env = env_from(&[("REPL_ID", "x")]);
        assert_eq!(detect_with(env, |_| false).unwrap().id, AgentId::Replit);
    }

    #[test]
    fn github_copilot_detected_via_each_var() {
        for var in ["COPILOT_MODEL", "COPILOT_ALLOW_ALL", "COPILOT_GITHUB_TOKEN"] {
            let env = env_from(&[(var, "1")]);
            let agent = detect_with(env, |_| false).unwrap();
            assert_eq!(agent.id, AgentId::GitHubCopilot, "var={var}");
        }
    }

    #[test]
    fn claude_code_session_id_extracted() {
        let env = env_from(&[
            ("CLAUDECODE", "1"),
            (
                "CLAUDE_CODE_SESSION_ID",
                "c3bb91d6-b133-4b8f-8ef5-7b4824bf9e00",
            ),
        ]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::ClaudeCode);
        assert_eq!(
            agent.session_id.as_deref(),
            Some("c3bb91d6-b133-4b8f-8ef5-7b4824bf9e00")
        );
    }

    #[test]
    fn session_id_resolved_on_generic_var_path() {
        // Claude Code identifies via AI_AGENT=claude-code_<ver>_agent, which
        // short-circuits before TOOL_VARS; the session id must still resolve.
        let env = env_from(&[
            ("AI_AGENT", "claude-code_2.1.179_agent"),
            ("CLAUDE_CODE_SESSION_ID", "abc"),
        ]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::ClaudeCode);
        assert_eq!(agent.session_id.as_deref(), Some("abc"));
    }

    #[test]
    fn session_id_none_when_agent_has_no_session_var() {
        let env = env_from(&[("AGENT", "goose")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::Goose);
        assert_eq!(agent.session_id, None);
    }

    #[test]
    fn session_id_none_when_var_absent() {
        let env = env_from(&[("CLAUDECODE", "1")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::ClaudeCode);
        assert_eq!(agent.session_id, None);
    }

    #[test]
    fn codex_thread_id_is_session_id() {
        let env = env_from(&[("CODEX_THREAD_ID", "th-123")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::Codex);
        assert_eq!(agent.session_id.as_deref(), Some("th-123"));
    }

    #[test]
    fn amp_session_id_prefers_current_thread_then_falls_back() {
        let env = env_from(&[("AMP_CURRENT_THREAD_ID", "T-primary")]);
        assert_eq!(
            detect_with(env, |_| false).unwrap().session_id.as_deref(),
            Some("T-primary")
        );

        // AGENT_THREAD_ID is the documented fallback when the primary is unset.
        // Amp still needs an identifying marker; AGENT=amp provides it.
        let env = env_from(&[("AGENT", "amp"), ("AGENT_THREAD_ID", "T-fallback")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::Amp);
        assert_eq!(agent.session_id.as_deref(), Some("T-fallback"));
    }

    #[test]
    fn qwen_code_session_id_extracted() {
        let env = env_from(&[("QWEN_CODE", "1"), ("QWEN_CODE_SESSION_ID", "q-1")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::QwenCode);
        assert_eq!(agent.session_id.as_deref(), Some("q-1"));
    }

    #[test]
    fn cursor_trace_id_doubles_as_session_id() {
        let env = env_from(&[
            ("CURSOR_TRACE_ID", "trace-9"),
            ("PAGER", "head -n 10000 | cat"),
        ]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::Cursor);
        assert_eq!(agent.session_id.as_deref(), Some("trace-9"));
    }

    #[test]
    fn copilot_session_id_extracted() {
        let env = env_from(&[("COPILOT_AGENT_SESSION_ID", "sess-7")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::GitHubCopilot);
        assert_eq!(agent.session_id.as_deref(), Some("sess-7"));
    }

    #[test]
    fn traceparent_surfaced_and_trace_id_parsed() {
        let tp = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01";
        let env = env_from(&[("CLAUDECODE", "1"), ("TRACEPARENT", tp)]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.traceparent.as_deref(), Some(tp));
        assert_eq!(agent.trace_id(), Some("0af7651916cd43dd8448eb211c80319c"));
    }

    #[test]
    fn traceparent_none_when_unset() {
        let env = env_from(&[("CLAUDECODE", "1")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.traceparent, None);
        assert_eq!(agent.trace_id(), None);
    }

    #[test]
    fn traceparent_read_for_any_detected_agent() {
        // It's a standard var, not agent-specific: surfaced even for agents
        // that never set it themselves but inherited it from the shell.
        let tp = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01";
        let env = env_from(&[("AGENT", "goose"), ("TRACEPARENT", tp)]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::Goose);
        assert_eq!(agent.traceparent.as_deref(), Some(tp));
    }

    #[test]
    fn trace_id_rejects_malformed_traceparent() {
        for bad in [
            "garbage",
            "00-tooshort-b7ad6b7169203331-01",
            // all-zero trace-id is invalid per the spec
            "00-00000000000000000000000000000000-b7ad6b7169203331-01",
            // non-hex digit in the trace-id
            "00-0af7651916cd43dd8448eb211c80319g-b7ad6b7169203331-01",
        ] {
            let env = env_from(&[("CLAUDECODE", "1"), ("TRACEPARENT", bad)]);
            let agent = detect_with(env, |_| false).unwrap();
            assert_eq!(agent.trace_id(), None, "traceparent={bad}");
        }
    }

    #[test]
    fn as_str_returns_url_safe_slug() {
        assert_eq!(AgentId::ClaudeCode.as_str(), "claude-code");
        assert_eq!(AgentId::CursorCli.as_str(), "cursor-cli");
        assert_eq!(AgentId::GitHubCopilot.as_str(), "github-copilot");
        assert_eq!(AgentId::Goose.as_str(), "goose");
        assert_eq!(AgentId::Unknown.as_str(), "unknown");
    }

    #[test]
    fn as_str_round_trips_through_agent_var() {
        for id in [
            AgentId::ClaudeCode,
            AgentId::Cursor,
            AgentId::CursorCli,
            AgentId::GeminiCli,
            AgentId::Codex,
            AgentId::Augment,
            AgentId::Cline,
            AgentId::OpenCode,
            AgentId::Trae,
            AgentId::Goose,
            AgentId::Amp,
            AgentId::Devin,
            AgentId::Replit,
            AgentId::Antigravity,
            AgentId::GitHubCopilot,
            AgentId::Crush,
            AgentId::QwenCode,
            AgentId::IflowCli,
            AgentId::AmazonQCli,
            AgentId::RooCode,
        ] {
            let slug = id.as_str();
            let env = env_from(&[("AGENT", slug)]);
            assert_eq!(
                detect_with(env, |_| false).unwrap().id,
                id,
                "slug {slug} did not round-trip"
            );
        }
    }

    #[test]
    fn agent_var_classifies_new_names() {
        for (val, expected) in [
            ("replit", AgentId::Replit),
            ("antigravity", AgentId::Antigravity),
            ("github-copilot", AgentId::GitHubCopilot),
            ("github-copilot-cli", AgentId::GitHubCopilot),
            ("cursor-cli", AgentId::CursorCli),
            ("augment-cli", AgentId::Augment),
            ("crush", AgentId::Crush),
            ("qwen", AgentId::QwenCode),
            ("iflow", AgentId::IflowCli),
            ("amazonq", AgentId::AmazonQCli),
            ("roo", AgentId::RooCode),
        ] {
            let env = env_from(&[("AGENT", val)]);
            assert_eq!(
                detect_with(env, |_| false).unwrap().id,
                expected,
                "val={val}"
            );
        }
    }
}
