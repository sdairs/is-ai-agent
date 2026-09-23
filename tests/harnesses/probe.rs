//! Small, deliberately redacted probe for tests/harnesses. Never dump `Agent`
//! with Debug: a matched signal can contain a credential in older releases.
use is_ai_agent::{Signal, detect, detect_with};
use std::{env, fs::OpenOptions, io::Write};

const MARKERS: &[&str] = &[
    "PI_CODING_AGENT",
    "PI_SESSION_ID",
    "QWEN_CODE",
    "GEMINI_CLI",
    "QWEN_CODE_SESSION_ID",
    "OPENCODE",
    "OPENCODE_PID",
    "COPILOT_CLI",
    "COPILOT_AGENT",
    "COPILOT_AGENT_SESSION_ID",
    "CRUSH",
    "GOOSE_TERMINAL",
    "CLINE_ACTIVE",
    "CLINE_TASK_ID",
    "CODEX_THREAD_ID",
    "CODEX_SESSION_ID",
    "CODEX_SANDBOX",
    "CLAUDECODE",
    "CLAUDE_CODE_CHILD_SESSION",
    "CLAUDE_CODE_SESSION_ID",
    "DSH_SHELL",
    "DSH_SESSION_ID",
    "KILO",
    "OPENCLAW_SHELL",
    "HERMES_AGENT",
    "HERMES_SESSION_ID",
    "VTCODE",
    "JUNIE_SHIM_PATH",
    "MATTERHORN_SESSION_ID",
];
// Predicate results only: never serialize arbitrary marker values.
const EXACT_MARKERS: &[(&str, &str)] = &[
    ("DSH_SHELL", "1"),
    ("KILO", "1"),
    ("OPENCLAW_SHELL", "exec"),
    ("HERMES_AGENT", "true"),
    ("VTCODE", "1"),
];
const SESSIONS: &[&str] = &[
    "PI_SESSION_ID",
    "QWEN_CODE_SESSION_ID",
    "COPILOT_AGENT_SESSION_ID",
    "CLINE_TASK_ID",
    "CODEX_THREAD_ID",
    "CLAUDE_CODE_SESSION_ID",
    "DSH_SESSION_ID",
    "HERMES_SESSION_ID",
];

fn nonblank(name: &str) -> Option<String> {
    env::var(name).ok().filter(|v| !v.trim().is_empty())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    if !(args.len() == 3 || (args.len() == 4 && args[3] == "--discover"))
        || args[2].len() != 32
        || !args[2].bytes().all(|b| b.is_ascii_hexdigit())
    {
        return Err("usage: probe OUTPUT_FILE 32_HEX_NONCE [--discover]".into());
    }
    let agent = detect();
    // These strings come from library constants, never from environment values.
    let id = agent
        .as_ref()
        .map_or("null".into(), |a| format!("\"{}\"", a.id.as_str()));
    let signal = agent.as_ref().map_or("null".into(), |a| match &a.signal {
        Signal::EnvVar { name, .. } => format!("\"{name}\""),
        Signal::File { .. } => "\"filesystem\"".into(),
        _ => "null".into(),
    });
    let session = agent.as_ref().and_then(|a| a.session_id.as_deref());
    let markers = MARKERS
        .iter()
        .map(|name| format!("\"{name}\":{}", nonblank(name).is_some()))
        .collect::<Vec<_>>()
        .join(",");
    let exact_markers = EXACT_MARKERS
        .iter()
        .map(|(name, expected)| {
            format!(
                "\"{name}\":{}",
                env::var(name).ok().as_deref() == Some(*expected)
            )
        })
        .collect::<Vec<_>>()
        .join(",");
    let sessions = SESSIONS
        .iter()
        .map(|name| {
            format!(
                "\"{name}\":{}",
                session.is_some() && session == nonblank(name).as_deref()
            )
        })
        .collect::<Vec<_>>()
        .join(",");
    // Classify each generic variable independently, even when another signal
    // wins detection. Only library-owned canonical names leave the container.
    let generic = ["AGENT", "AI_AGENT"]
        .iter()
        .map(|name| {
            let recognized = detect_with(
                |key| (key == *name).then(|| env::var(key).ok()).flatten(),
                |_| false,
            );
            let identity = recognized.map_or("null".into(), |a| format!("\"{}\"", a.id.as_str()));
            format!("\"{name}\":{identity}")
        })
        .collect::<Vec<_>>()
        .join(",");
    let record = format!(
        concat!(
            "{{\"schema\":4,\"nonce\":\"{}\",\"library_version\":\"{}\",",
            "\"agent\":{},\"signal\":{},\"session_present\":{},",
            "\"markers\":{{{}}},\"exact_markers\":{{{}}},\"session_matches\":{{{}}},\"generic_markers\":{{{}}}}}\n"
        ),
        args[2],
        env!("CARGO_PKG_VERSION"),
        id,
        signal,
        session.is_some(),
        markers,
        exact_markers,
        sessions,
        generic,
    );
    // A stale or duplicated invocation cannot silently overwrite evidence.
    OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&args[1])?
        .write_all(record.as_bytes())?;
    print!("{record}");
    if args.len() == 4 {
        // Installed only in the isolated test image. A separate artifact keeps
        // the detector contract and diagnostic observations distinct.
        let status = std::process::Command::new("/usr/local/bin/node")
            .args([
                "/opt/discover.mjs",
                &format!("{}.discovery.json", args[1]),
                &args[2],
            ])
            .status()?;
        if !status.success() {
            return Err("discovery failed".into());
        }
    }
    Ok(())
}
