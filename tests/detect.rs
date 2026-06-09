use is_ai_agent::{Agent, AgentId, Signal, detect_with};

#[test]
fn public_api_detects_via_agent_var() {
    let agent: Agent = detect_with(
        |name| {
            if name == "AGENT" {
                Some("amp".into())
            } else {
                None
            }
        },
        |_| false,
    )
    .expect("agent detected");

    assert_eq!(agent.id, AgentId::Amp);
    assert_eq!(agent.name, "Amp");
    match agent.signal {
        Signal::EnvVar { name, value } => {
            assert_eq!(name, "AGENT");
            assert_eq!(value, "amp");
        }
        _ => panic!("expected env var signal"),
    }
}

#[test]
fn public_api_detects_via_tool_var() {
    let agent = detect_with(
        |name| {
            if name == "CLAUDECODE" {
                Some("1".into())
            } else {
                None
            }
        },
        |_| false,
    )
    .unwrap();

    assert_eq!(agent.id, AgentId::ClaudeCode);
}

#[test]
fn public_api_detects_via_file() {
    let agent = detect_with(|_| None, |p| p == "/opt/.devin").unwrap();
    assert_eq!(agent.id, AgentId::Devin);
}

#[test]
fn public_api_returns_none_with_no_signals() {
    assert!(detect_with(|_| None, |_| false).is_none());
}
