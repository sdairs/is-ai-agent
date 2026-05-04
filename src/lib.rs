//! Detect whether the current process is being invoked by an AI coding agent,
//! and identify which one.
//!
//! Detection order:
//! 1. The proposed standard `AGENT` env var (see agentsmd/agents.md#136).
//! 2. Tool-specific env vars (`CLAUDECODE`, `CURSOR_AGENT`, ...).
//! 3. Filesystem signals (e.g. `/opt/.devin`).
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
    ("CLAUDECODE", AgentId::ClaudeCode, "Claude Code"),
    ("CLAUDE_CODE", AgentId::ClaudeCode, "Claude Code"),
    ("CURSOR_TRACE_ID", AgentId::Cursor, "Cursor"),
    ("CURSOR_AGENT", AgentId::CursorCli, "Cursor CLI"),
    ("GEMINI_CLI", AgentId::GeminiCli, "Gemini CLI"),
    ("CODEX_SANDBOX", AgentId::Codex, "OpenAI Codex"),
    ("CODEX_CI", AgentId::Codex, "OpenAI Codex"),
    ("CODEX_THREAD_ID", AgentId::Codex, "OpenAI Codex"),
    ("ANTIGRAVITY_AGENT", AgentId::Antigravity, "Antigravity"),
    ("AUGMENT_AGENT", AgentId::Augment, "Augment"),
    ("CLINE_ACTIVE", AgentId::Cline, "Cline"),
    ("OPENCODE_CLIENT", AgentId::OpenCode, "OpenCode"),
    ("TRAE_AI_SHELL_ID", AgentId::Trae, "TRAE AI"),
    ("GOOSE_TERMINAL", AgentId::Goose, "Goose"),
    ("REPL_ID", AgentId::Replit, "Replit"),
    ("COPILOT_MODEL", AgentId::GitHubCopilot, "GitHub Copilot"),
    ("COPILOT_ALLOW_ALL", AgentId::GitHubCopilot, "GitHub Copilot"),
    ("COPILOT_GITHUB_TOKEN", AgentId::GitHubCopilot, "GitHub Copilot"),
];

const FILE_SIGNALS: &[(&str, AgentId, &str)] = &[("/opt/.devin", AgentId::Devin, "Devin")];

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
    if let Some(value) = nonempty(env("AGENT")) {
        let (id, name) = classify_agent_value(&value);
        return Some(Agent {
            id,
            name,
            signal: Signal::EnvVar { name: "AGENT", value },
        });
    }

    // Special-cased value match: Cursor's extension host signals an agent
    // execution context only when the value equals "agent-exec".
    if let Some(value) = nonempty(env("CURSOR_EXTENSION_HOST_ROLE")) {
        if value.trim() == "agent-exec" {
            return Some(Agent {
                id: AgentId::CursorCli,
                name: "Cursor CLI",
                signal: Signal::EnvVar {
                    name: "CURSOR_EXTENSION_HOST_ROLE",
                    value,
                },
            });
        }
    }

    for &(var, id, name) in TOOL_VARS {
        if let Some(value) = nonempty(env(var)) {
            return Some(Agent {
                id,
                name,
                signal: Signal::EnvVar { name: var, value },
            });
        }
    }

    for &(path, id, name) in FILE_SIGNALS {
        if file_exists(path) {
            return Some(Agent {
                id,
                name,
                signal: Signal::File { path },
            });
        }
    }

    None
}

fn nonempty(v: Option<String>) -> Option<String> {
    v.filter(|s| !s.is_empty())
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
            Signal::EnvVar { name: "AGENT", value: "goose".to_string() }
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
        assert_eq!(agent.id, AgentId::CursorCli);
        assert_eq!(
            agent.signal,
            Signal::EnvVar { name: "CURSOR_AGENT", value: "1".to_string() }
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
        assert_eq!(agent.signal, Signal::File { path: "/opt/.devin" });
    }

    #[test]
    fn env_vars_take_priority_over_files() {
        let env = env_from(&[("CLAUDECODE", "1")]);
        assert_eq!(
            detect_with(env, |_| true).unwrap().id,
            AgentId::ClaudeCode
        );
    }

    #[test]
    fn claude_code_alias_var_detected() {
        let env = env_from(&[("CLAUDE_CODE", "1")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::ClaudeCode);
        assert_eq!(
            agent.signal,
            Signal::EnvVar { name: "CLAUDE_CODE", value: "1".to_string() }
        );
    }

    #[test]
    fn cursor_editor_detected_via_trace_id() {
        let env = env_from(&[("CURSOR_TRACE_ID", "abc123")]);
        let agent = detect_with(env, |_| false).unwrap();
        assert_eq!(agent.id, AgentId::Cursor);
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
        ] {
            let env = env_from(&[("AGENT", val)]);
            assert_eq!(detect_with(env, |_| false).unwrap().id, expected, "val={val}");
        }
    }
}
