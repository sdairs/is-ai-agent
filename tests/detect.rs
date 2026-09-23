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

#[test]
fn pi_shell_session_is_a_fallback_and_preserves_opaque_value() {
    for marker in [None, Some("AI_AGENT"), Some("PI_CODING_AGENT")] {
        let agent = detect_with(
            |name| match name {
                "PI_SESSION_ID" => Some(" session-1 ".into()),
                "AI_AGENT" if marker == Some(name) => Some("pi".into()),
                "PI_CODING_AGENT" if marker == Some(name) => Some("true".into()),
                _ => None,
            },
            |_| false,
        )
        .unwrap();
        assert_eq!(agent.id, AgentId::Pi);
        assert_eq!(agent.session_id.as_deref(), Some(" session-1 "));
    }
}

#[test]
fn pi_blank_sessions_are_ignored() {
    for value in ["", " ", "\t\n"] {
        assert!(
            detect_with(
                |name| (name == "PI_SESSION_ID").then(|| value.into()),
                |_| false
            )
            .is_none()
        );
        let agent = detect_with(
            |name| match name {
                "AI_AGENT" => Some("pi".into()),
                "PI_SESSION_ID" => Some(value.into()),
                _ => None,
            },
            |_| false,
        )
        .unwrap();
        assert_eq!(agent.session_id, None);
    }
}

#[test]
fn pi_session_does_not_override_other_identity_or_leak_into_it() {
    for marker in ["AI_AGENT", "CODEX_THREAD_ID"] {
        let agent = detect_with(
            |name| {
                if name == marker {
                    Some("codex".into())
                } else if name == "PI_SESSION_ID" {
                    Some("pi-session".into())
                } else {
                    None
                }
            },
            |_| false,
        )
        .unwrap();
        assert_eq!(agent.id, AgentId::Codex);
        assert_ne!(agent.session_id.as_deref(), Some("pi-session"));
    }
}

#[test]
fn pi_session_is_read_on_each_call() {
    for session in ["one", "two"] {
        let agent = detect_with(
            |name| (name == "PI_SESSION_ID").then(|| session.into()),
            |_| false,
        )
        .unwrap();
        assert_eq!(agent.session_id.as_deref(), Some(session));
    }
}
