//! Small, deliberately redacted probe for tests/harnesses. Never dump `Agent`
//! with Debug: a matched signal can contain a credential in older releases.
use is_ai_agent::{Signal, detect};
use std::{env, fs::OpenOptions, io::Write};

const MARKERS: &[&str] = &[
    "PI_CODING_AGENT",
    "PI_SESSION_ID",
    "QWEN_CODE",
    "GEMINI_CLI",
    "QWEN_CODE_SESSION_ID",
    "OPENCODE",
    "OPENCODE_PID",
];
const SESSIONS: &[&str] = &["PI_SESSION_ID", "QWEN_CODE_SESSION_ID"];

fn nonblank(name: &str) -> Option<String> {
    env::var(name).ok().filter(|v| !v.trim().is_empty())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    if args.len() != 3 || args[2].len() != 32 || !args[2].bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err("usage: probe OUTPUT_FILE 32_HEX_NONCE".into());
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
    let record = format!(
        concat!(
            "{{\"schema\":2,\"nonce\":\"{}\",\"library_version\":\"{}\",",
            "\"agent\":{},\"signal\":{},\"session_present\":{},",
            "\"markers\":{{{}}},\"session_matches\":{{{}}}}}\n"
        ),
        args[2],
        env!("CARGO_PKG_VERSION"),
        id,
        signal,
        session.is_some(),
        markers,
        sessions,
    );
    // A stale or duplicated invocation cannot silently overwrite evidence.
    OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&args[1])?
        .write_all(record.as_bytes())?;
    print!("{record}");
    Ok(())
}
