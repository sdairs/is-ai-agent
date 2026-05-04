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
pub struct Agent {
    pub id: AgentId,
    pub name: &'static str,
    pub signal: Signal,
}

/// Canonical identifier for a known agent, or `Unknown` when an agent is
/// present but its specific identity can't be determined (e.g. `AGENT=1`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum AgentId {
    ClaudeCode,
    Cursor,
    GeminiCli,
    Codex,
    Augment,
    Cline,
    OpenCode,
    Trae,
    Goose,
    Amp,
    Devin,
    Unknown,
}

/// What signal triggered the detection.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Signal {
    EnvVar { name: &'static str, value: String },
    File { path: &'static str },
}

const TOOL_VARS: &[(&str, AgentId, &str)] = &[
    ("CLAUDECODE", AgentId::ClaudeCode, "Claude Code"),
    ("CURSOR_AGENT", AgentId::Cursor, "Cursor"),
    ("GEMINI_CLI", AgentId::GeminiCli, "Gemini CLI"),
    ("CODEX_SANDBOX", AgentId::Codex, "OpenAI Codex"),
    ("AUGMENT_AGENT", AgentId::Augment, "Augment"),
    ("CLINE_ACTIVE", AgentId::Cline, "Cline"),
    ("OPENCODE_CLIENT", AgentId::OpenCode, "OpenCode"),
    ("TRAE_AI_SHELL_ID", AgentId::Trae, "TRAE AI"),
    ("GOOSE_TERMINAL", AgentId::Goose, "Goose"),
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
        "gemini" | "gemini-cli" => (AgentId::GeminiCli, "Gemini CLI"),
        "codex" => (AgentId::Codex, "OpenAI Codex"),
        "augment" => (AgentId::Augment, "Augment"),
        "cline" => (AgentId::Cline, "Cline"),
        "opencode" => (AgentId::OpenCode, "OpenCode"),
        "trae" => (AgentId::Trae, "TRAE AI"),
        "devin" => (AgentId::Devin, "Devin"),
        _ => (AgentId::Unknown, "AI agent"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    fn env_from(pairs: &[(&str, &str)]) -> impl Fn(&str) -> Option<String> {
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
        assert_eq!(agent.id, AgentId::Cursor);
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
}
