//! Demonstrates how a CLI can branch its output based on the agent.
//!
//! Run with: `cargo run --example detect`
//! Or:       `AGENT=goose cargo run --example detect`
//! Or:       `DSH_SHELL=1 DSH_SESSION_ID=demo cargo run --example detect`
//!
//! Inherited markers attribute a process to a harness; they do not prove that
//! a model requested this command. No match does not prove a human caller.

use is_ai_agent::{Signal, detect};

fn main() {
    match detect() {
        Some(agent) => {
            let source = match &agent.signal {
                Signal::EnvVar { name, value } => format!("env {name}={value}"),
                Signal::File { path } => format!("file {path}"),
                _ => "unknown signal".to_string(),
            };
            println!(
                "agent: {} ({}) via {}",
                agent.name,
                agent.id.as_str(),
                source
            );
            // Correlate using both the harness identity and its opaque id.
            // Codex returns a thread id, never its shared root-session id.
            match &agent.session_id {
                Some(id) => println!("session: {}:{id}", agent.id.as_str()),
                None => println!("session: <none available>"),
            }
            if let Some(trace_id) = agent.trace_id() {
                println!("trace: {trace_id}");
            }
            println!(r#"{{"error":"config_missing","suggestion":"run ./setup.sh"}}"#);
        }
        None => {
            println!("no AI agent detected");
            println!("Error: Config file not found. Run ./setup.sh to initialize.");
        }
    }
}
