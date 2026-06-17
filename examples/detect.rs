//! Demonstrates how a CLI can branch its output based on the agent.
//!
//! Run with: `cargo run --example detect`
//! Or:       `AGENT=goose cargo run --example detect`

use is_ai_agent::{Signal, detect};

fn main() {
    match detect() {
        Some(agent) => {
            let source = match &agent.signal {
                Signal::EnvVar { name, value } => format!("env {name}={value}"),
                Signal::File { path } => format!("file {path}"),
                _ => "unknown signal".to_string(),
            };
            println!("agent: {} ({:?}) via {}", agent.name, agent.id, source);
            match &agent.session_id {
                Some(id) => println!("session: {id}"),
                None => println!("session: <none exposed>"),
            }
            println!(r#"{{"error":"config_missing","suggestion":"run ./setup.sh"}}"#);
        }
        None => {
            println!("no AI agent detected");
            println!("Error: Config file not found. Run ./setup.sh to initialize.");
        }
    }
}
