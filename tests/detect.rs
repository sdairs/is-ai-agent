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

fn captured_env(vars: &[(&str, &str)]) -> Option<Agent> {
    detect_with(
        |name| {
            vars.iter()
                .find(|(key, _)| *key == name)
                .map(|(_, value)| (*value).to_owned())
        },
        |_| false,
    )
}

fn assert_env_signal(agent: &Agent, name: &'static str, value: &str) {
    assert_eq!(
        agent.signal,
        Signal::EnvVar {
            name,
            value: value.to_owned(),
        }
    );
}

#[test]
fn generic_blank_and_false_values_are_ignored() {
    for var in ["AGENT", "AI_AGENT"] {
        for value in [
            "", " ", "\t\r\n", "0", "false", "no", "off", " FALSE ", "No", "oFf\n", "\t0 ",
        ] {
            assert!(
                captured_env(&[(var, value)]).is_none(),
                "{var}={value:?} must not establish identity"
            );
            let agent = captured_env(&[(var, value), ("CLAUDECODE", "1")]).unwrap();
            assert_eq!(agent.id, AgentId::ClaudeCode, "{var}={value:?}");
            assert_env_signal(&agent, "CLAUDECODE", "1");
        }
    }
    let agent = captured_env(&[("AGENT", "false"), ("AI_AGENT", "codex")]).unwrap();
    assert_eq!(agent.id, AgentId::Codex);
}

#[test]
fn unknown_names_and_bare_truth_remain_fallbacks_with_original_values() {
    for var in ["AGENT", "AI_AGENT"] {
        for value in [
            "1",
            "true",
            " TRUE ",
            "yes",
            "unknown-harness",
            "  future-agent@1.0  ",
        ] {
            let agent = captured_env(&[(var, value)]).unwrap();
            assert_eq!(agent.id, AgentId::Unknown, "{var}={value:?}");
            assert_env_signal(&agent, var, value);

            let agent = captured_env(&[(var, value), ("VTCODE", "1")]).unwrap();
            assert_eq!(agent.id, AgentId::VTCode, "{var}={value:?}");
        }
    }
    // The first generic fallback still wins if neither names a known agent.
    let agent = captured_env(&[("AGENT", "outer-unknown"), ("AI_AGENT", "inner-unknown")]).unwrap();
    assert_env_signal(&agent, "AGENT", "outer-unknown");
    // A known AI_AGENT is more informative than the earlier Unknown fallback.
    let agent = captured_env(&[("AGENT", "outer-unknown"), ("AI_AGENT", "hermes")]).unwrap();
    assert_eq!(agent.id, AgentId::Hermes);
}

#[test]
fn known_generic_identity_preserves_agent_then_ai_agent_precedence() {
    let agent = captured_env(&[
        ("AGENT", "codex"),
        ("AI_AGENT", "hermes-agent"),
        ("HERMES_AGENT", "true"),
        ("HERMES_SESSION_ID", "hermes-session"),
    ])
    .unwrap();
    assert_eq!(agent.id, AgentId::Codex);
    assert_eq!(agent.session_id, None);
    assert_env_signal(&agent, "AGENT", "codex");

    let agent = captured_env(&[
        ("AI_AGENT", "codex"),
        ("HERMES_AGENT", "true"),
        ("HERMES_SESSION_ID", "hermes-session"),
    ])
    .unwrap();
    assert_eq!(agent.id, AgentId::Codex);
    assert_eq!(agent.session_id, None);
    assert_env_signal(&agent, "AI_AGENT", "codex");
}

#[test]
fn removed_config_credential_and_workspace_signals_do_not_detect() {
    for (var, value) in [
        ("COPILOT_GITHUB_TOKEN", "synthetic-token-do-not-log"),
        ("COPILOT_MODEL", "example-model"),
        ("COPILOT_ALLOW_ALL", "1"),
        ("REPL_ID", "workspace-id"),
        ("REPLIT_MODE", "assistant"),
        ("GROK_AGENT", "custom-profile"),
    ] {
        assert!(captured_env(&[(var, value)]).is_none(), "{var}");
    }
}

#[test]
fn ignored_copilot_token_never_enters_the_public_result() {
    let token = "synthetic-token-do-not-log";
    for (var, value, expected) in [
        ("COPILOT_CLI", "1", AgentId::GitHubCopilot),
        ("VTCODE", "1", AgentId::VTCode),
        ("AI_AGENT", "codex", AgentId::Codex),
    ] {
        let agent = captured_env(&[("COPILOT_GITHUB_TOKEN", token), (var, value)]).unwrap();
        assert_eq!(agent.id, expected);
        assert_env_signal(&agent, var, value);
        assert_eq!(agent.session_id, None);
        assert_eq!(agent.traceparent, None);
        assert!(!format!("{agent:?}").contains(token));
    }
}

#[test]
fn new_exact_markers_accept_only_the_documented_literal_value() {
    for (var, value, id) in [
        ("DSH_SHELL", "1", AgentId::DeepSeekHarness),
        ("HERMES_AGENT", "true", AgentId::Hermes),
        ("OPENCLAW_SHELL", "exec", AgentId::OpenClaw),
        ("KILO", "1", AgentId::KiloCode),
        ("VTCODE", "1", AgentId::VTCode),
        ("CLAUDE_CODE_CHILD_SESSION", "1", AgentId::ClaudeCode),
    ] {
        let agent = captured_env(&[(var, value)]).unwrap();
        assert_eq!(agent.id, id, "{var}");
        assert_env_signal(&agent, var, value);
        for incorrect in [
            "",
            " ",
            "0",
            "false",
            "TRUE",
            "EXEC",
            "arbitrary",
            "1 ",
            " true",
            "exec\n",
        ] {
            assert!(
                captured_env(&[(var, incorrect)]).is_none(),
                "{var}={incorrect:?} must not match"
            );
        }
    }
}

#[test]
fn openclaw_non_exec_shell_modes_do_not_detect() {
    for mode in ["tui-local", "acp-client", "acp", "exec-client"] {
        assert!(
            captured_env(&[("OPENCLAW_SHELL", mode)]).is_none(),
            "{mode}"
        );
    }
}

#[test]
fn opaque_identity_values_require_nonblank_and_preserve_the_original() {
    for (var, id, has_session) in [
        ("HERMES_SESSION_ID", AgentId::Hermes, true),
        ("GROK_SESSION_ID", AgentId::GrokBuild, true),
        ("PI_SESSION_ID", AgentId::Pi, true),
        ("CODEX_SESSION_ID", AgentId::Codex, false),
        ("JUNIE_SHIM_PATH", AgentId::Junie, false),
    ] {
        for blank in ["", " ", "\t\r\n"] {
            assert!(captured_env(&[(var, blank)]).is_none(), "{var}={blank:?}");
        }
        for opaque in ["opaque-id-or-path", "  opaque-id-or-path\t"] {
            let agent = captured_env(&[(var, opaque)]).unwrap();
            assert_eq!(agent.id, id, "{var}");
            assert_env_signal(&agent, var, opaque);
            assert_eq!(
                agent.session_id.as_deref(),
                has_session.then_some(opaque),
                "{var}"
            );
        }
    }
}

#[test]
fn deepseek_session_requires_identity_and_never_uses_the_pty_id() {
    for session in [
        None,
        Some(""),
        Some(" \t"),
        Some("session-1"),
        Some(" session-2 "),
    ] {
        let mut vars = vec![("DSH_SHELL", "1"), ("DSH_PTY_SESSION_ID", "pty-only")];
        if let Some(value) = session {
            vars.push(("DSH_SESSION_ID", value));
        }
        let agent = captured_env(&vars).unwrap();
        assert_eq!(agent.id, AgentId::DeepSeekHarness);
        assert_eq!(
            agent.session_id.as_deref(),
            session.filter(|value| !value.trim().is_empty())
        );
    }
    for var in [
        "DSH_SESSION_ID",
        "DSH_PTY_SESSION_ID",
        "DSH_HOME",
        "DSH_PROFILE",
        "DSH_PROFILE_DIR",
        "DEEPSEEK_API_KEY",
    ] {
        assert!(captured_env(&[(var, "synthetic-value")]).is_none(), "{var}");
    }
    let agent = captured_env(&[("AGENT", "dsh"), ("DSH_SESSION_ID", "session-3")]).unwrap();
    assert_eq!(agent.id, AgentId::DeepSeekHarness);
    assert_eq!(agent.session_id.as_deref(), Some("session-3"));
}

#[test]
fn new_session_sources_work_with_explicit_identity_and_ignore_blank_ids() {
    for (slug, session_var, id) in [
        (
            "deepseek-harness",
            "DSH_SESSION_ID",
            AgentId::DeepSeekHarness,
        ),
        ("hermes-agent", "HERMES_SESSION_ID", AgentId::Hermes),
        ("grok-build", "GROK_SESSION_ID", AgentId::GrokBuild),
        ("pi", "PI_SESSION_ID", AgentId::Pi),
    ] {
        for session in ["", " \t", "session-1", " session-2 "] {
            let agent = captured_env(&[("AI_AGENT", slug), (session_var, session)]).unwrap();
            assert_eq!(agent.id, id);
            assert_eq!(
                agent.session_id.as_deref(),
                (!session.trim().is_empty()).then_some(session)
            );
            assert_env_signal(&agent, "AI_AGENT", slug);
        }
    }
}

#[test]
fn hermes_prefers_its_execution_marker_to_the_older_session_fallback() {
    let agent =
        captured_env(&[("HERMES_AGENT", "true"), ("HERMES_SESSION_ID", "hermes-1")]).unwrap();
    assert_eq!(agent.id, AgentId::Hermes);
    assert_eq!(agent.session_id.as_deref(), Some("hermes-1"));
    assert_env_signal(&agent, "HERMES_AGENT", "true");

    let agent =
        captured_env(&[("HERMES_AGENT", "false"), ("HERMES_SESSION_ID", "hermes-1")]).unwrap();
    assert_eq!(agent.id, AgentId::Hermes);
    assert_env_signal(&agent, "HERMES_SESSION_ID", "hermes-1");
}

#[test]
fn pi_session_fallback_agrees_with_its_existing_marker() {
    let agent =
        captured_env(&[("PI_CODING_AGENT", "true"), ("PI_SESSION_ID", "pi-session")]).unwrap();
    assert_eq!(agent.id, AgentId::Pi);
    assert_eq!(agent.session_id.as_deref(), Some("pi-session"));
}

#[test]
fn codex_root_and_thread_ids_keep_distinct_correlation_semantics() {
    for (root, thread, expected_session) in [
        (Some("root-1"), None, None),
        (None, Some("thread-1"), Some("thread-1")),
        (Some("root-1"), Some("thread-1"), Some("thread-1")),
    ] {
        let mut vars = Vec::new();
        if let Some(value) = root {
            vars.push(("CODEX_SESSION_ID", value));
        }
        if let Some(value) = thread {
            vars.push(("CODEX_THREAD_ID", value));
        }
        let agent = captured_env(&vars).unwrap();
        assert_eq!(agent.id, AgentId::Codex);
        assert_eq!(agent.session_id.as_deref(), expected_session);
    }
}

#[test]
fn routing_run_and_trace_metadata_are_not_new_conversation_ids() {
    for (identity, value, extra, id) in [
        ("KILO", "1", "KILO_RUN_ID", AgentId::KiloCode),
        (
            "HERMES_AGENT",
            "true",
            "HERMES_SESSION_THREAD_ID",
            AgentId::Hermes,
        ),
        (
            "JUNIE_SHIM_PATH",
            "/synthetic/junie",
            "MATTERHORN_SESSION_ID",
            AgentId::Junie,
        ),
        (
            "DSH_SHELL",
            "1",
            "DSH_PTY_SESSION_ID",
            AgentId::DeepSeekHarness,
        ),
    ] {
        let agent = captured_env(&[
            (identity, value),
            (extra, "unrelated-id"),
            (
                "TRACEPARENT",
                "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
            ),
        ])
        .unwrap();
        assert_eq!(agent.id, id);
        assert_eq!(agent.session_id, None, "{extra}");
        assert_eq!(agent.trace_id(), Some("0af7651916cd43dd8448eb211c80319c"));
    }
}

#[test]
fn new_generic_names_display_names_and_canonical_slugs_round_trip() {
    for (id, name, slug, aliases) in [
        (
            AgentId::DeepSeekHarness,
            "DeepSeek Harness",
            "deepseek-harness",
            &["deepseek-harness", "dsh"][..],
        ),
        (
            AgentId::Hermes,
            "Hermes Agent",
            "hermes-agent",
            &["hermes-agent", "hermes"][..],
        ),
        (AgentId::OpenClaw, "OpenClaw", "openclaw", &["openclaw"][..]),
        (
            AgentId::GrokBuild,
            "Grok Build",
            "grok-build",
            &["grok-build"][..],
        ),
        (
            AgentId::KiloCode,
            "Kilo Code",
            "kilo-code",
            &["kilo-code", "kilo", "kilocode"][..],
        ),
        (AgentId::Junie, "Junie", "junie", &["junie"][..]),
        (AgentId::VTCode, "VTCode", "vtcode", &["vtcode"][..]),
    ] {
        assert_eq!(id.as_str(), slug);
        for var in ["AGENT", "AI_AGENT"] {
            for alias in aliases {
                for value in [
                    (*alias).to_owned(),
                    format!("{alias}@1.2.3"),
                    format!("{alias}_1.2.3_cli"),
                    format!(" {} ", alias.to_ascii_uppercase()),
                ] {
                    let agent = captured_env(&[(var, &value)]).unwrap();
                    assert_eq!(agent.id, id, "{var}={value}");
                    assert_eq!(agent.name, name, "{var}={value}");
                    assert_env_signal(&agent, var, &value);
                }
            }
        }
    }
}

#[test]
fn copilot_whole_name_aliases_and_removed_rule_identities_remain_supported() {
    for (value, id) in [
        ("github_copilot_app_agent", AgentId::GitHubCopilot),
        ("github_copilot_vscode_agent", AgentId::GitHubCopilot),
        ("grok", AgentId::GrokCli),
        ("grok-cli", AgentId::GrokCli),
        ("replit", AgentId::Replit),
    ] {
        for var in ["AGENT", "AI_AGENT"] {
            let agent = captured_env(&[(var, value)]).unwrap();
            assert_eq!(agent.id, id, "{var}={value}");
        }
    }
    assert_eq!(AgentId::GrokCli.as_str(), "grok-cli");
    assert_eq!(AgentId::Replit.as_str(), "replit");
}

#[test]
fn kilo_identity_precedes_inherited_opencode_and_generic_truth() {
    let agent = captured_env(&[("AGENT", "1"), ("KILO", "1"), ("OPENCODE", "1")]).unwrap();
    assert_eq!(agent.id, AgentId::KiloCode);
    assert_env_signal(&agent, "KILO", "1");

    let agent = captured_env(&[("KILO", "true"), ("OPENCODE", "1")]).unwrap();
    assert_eq!(agent.id, AgentId::OpenCode);

    let agent = captured_env(&[("AGENT", "opencode"), ("KILO", "1"), ("OPENCODE", "1")]).unwrap();
    assert_eq!(agent.id, AgentId::OpenCode);
    assert_env_signal(&agent, "AGENT", "opencode");
}

#[test]
fn claude_child_marker_preserves_derivative_and_cowork_precedence() {
    for (var, value, id) in [
        ("AMP_CURRENT_THREAD_ID", "amp-thread", AgentId::Amp),
        ("CODEBUDDY", "1", AgentId::CodeBuddy),
        ("CLAUDE_CODE_IS_COWORK", "1", AgentId::Cowork),
    ] {
        let agent = captured_env(&[
            (var, value),
            ("CLAUDE_CODE_CHILD_SESSION", "1"),
            ("CLAUDECODE", "1"),
        ])
        .unwrap();
        assert_eq!(agent.id, id, "{var}");
    }
    let agent = captured_env(&[("CLAUDE_CODE_CHILD_SESSION", "1"), ("CLAUDECODE", "1")]).unwrap();
    assert_env_signal(&agent, "CLAUDE_CODE_CHILD_SESSION", "1");

    let agent = captured_env(&[
        ("AI_AGENT", "claude-code_2.1.0_cli"),
        ("CLAUDE_CODE_IS_COWORK", "1"),
    ])
    .unwrap();
    assert_eq!(agent.id, AgentId::Cowork);

    let agent = captured_env(&[
        ("AMP_CURRENT_THREAD_ID", "amp-thread"),
        ("CLAUDE_CODE_IS_COWORK", "1"),
    ])
    .unwrap();
    assert_eq!(agent.id, AgentId::Amp);
}

#[test]
fn gemini_derivatives_keep_their_existing_precedence() {
    for (var, value, id) in [
        ("QWEN_CODE", "1", AgentId::QwenCode),
        ("VECLI_SANDBOX", "1", AgentId::VeCli),
        ("VECLI_DIR", "/synthetic/vecli", AgentId::VeCli),
    ] {
        let agent = captured_env(&[(var, value), ("GEMINI_CLI", "1")]).unwrap();
        assert_eq!(agent.id, id, "{var}");
    }
}

#[test]
fn guarded_cursor_signals_do_not_expand_into_bare_trace_detection() {
    assert!(captured_env(&[("CURSOR_TRACE_ID", "trace-id")]).is_none());
    assert!(captured_env(&[("CURSOR_TRACE_ID", "trace-id"), ("PAGER", "cat")]).is_none());
    assert!(captured_env(&[("CURSOR_EXTENSION_HOST_ROLE", "ui")]).is_none());

    let agent = captured_env(&[
        ("CURSOR_TRACE_ID", "trace-id"),
        ("PAGER", "head -n 10000 | cat"),
    ])
    .unwrap();
    assert_eq!(agent.id, AgentId::Cursor);
    assert_eq!(agent.session_id.as_deref(), Some("trace-id"));

    let agent = captured_env(&[
        ("CURSOR_AGENT", "1"),
        ("CURSOR_EXTENSION_HOST_ROLE", "agent-exec"),
    ])
    .unwrap();
    assert_eq!(agent.id, AgentId::CursorCli);
}

#[test]
fn openhands_explicit_identity_and_guarded_prompt_markers_still_work() {
    let agent = captured_env(&[("AI_AGENT", "openhands")]).unwrap();
    assert_eq!(agent.id, AgentId::OpenHands);
    for var in ["PS1", "PROMPT_COMMAND"] {
        let agent = captured_env(&[("AGENT", "1"), (var, "###PS1JSON###{}###PS1END###")]).unwrap();
        assert_eq!(agent.id, AgentId::OpenHands);
        assert!(captured_env(&[(var, "ordinary interactive prompt")]).is_none());
    }
}

#[test]
fn deferred_configuration_and_metadata_do_not_establish_identity() {
    for (var, value) in [
        ("QWEN_CODE_NO_RELAUNCH", "true"),
        ("QWEN_LIVE_HARNESS_CONFIG", "/synthetic/config"),
        ("QWEN_LIVE_HARNESS_API_KEY", "synthetic-key"),
        ("QWEN_CODE_MODEL", "example-model"),
        ("CODEX_VERSION", "0.156.1"),
        ("CODEX_PERMISSION_PROFILE", "workspace-write"),
        ("JUNIE_DATA", "/synthetic/junie"),
        ("MATTERHORN_SESSION_ID", "matterhorn-session"),
        ("KILO_RUN_ID", "kilo-run"),
        ("HERMES_SESSION_THREAD_ID", "messaging-thread"),
        ("PI_MODEL", "example-model"),
        ("PI_PROVIDER", "example-provider"),
        ("PI_CODING_AGENT_DIR", "/synthetic/pi"),
        ("GEMINI_CLI_SESSION_ID", "not-a-supported-export"),
        ("OPENCODE_SESSION_ID", "not-a-supported-export"),
        (
            "TRACEPARENT",
            "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
        ),
    ] {
        assert!(captured_env(&[(var, value)]).is_none(), "{var}");
    }
    // A delegating product's launch plumbing does not override the executor.
    let agent = captured_env(&[
        ("QWEN_CODE_NO_RELAUNCH", "true"),
        ("CODEX_SESSION_ID", "root-session"),
    ])
    .unwrap();
    assert_eq!(agent.id, AgentId::Codex);
}

#[test]
fn session_and_trace_metadata_are_fresh_on_every_detection_call() {
    for (slug, session_var, id) in [
        ("qwen-code", "QWEN_CODE_SESSION_ID", AgentId::QwenCode),
        ("pi", "PI_SESSION_ID", AgentId::Pi),
        ("hermes-agent", "HERMES_SESSION_ID", AgentId::Hermes),
        ("grok-build", "GROK_SESSION_ID", AgentId::GrokBuild),
        (
            "deepseek-harness",
            "DSH_SESSION_ID",
            AgentId::DeepSeekHarness,
        ),
        ("codex", "CODEX_THREAD_ID", AgentId::Codex),
    ] {
        for (session, trace) in [
            (
                "session-one",
                "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
            ),
            (
                "session-two",
                "00-1234567890abcdef1234567890abcdef-b7ad6b7169203331-01",
            ),
        ] {
            let agent = captured_env(&[
                ("AI_AGENT", slug),
                (session_var, session),
                ("TRACEPARENT", trace),
            ])
            .unwrap();
            assert_eq!(agent.id, id);
            assert_eq!(agent.session_id.as_deref(), Some(session));
            assert_eq!(agent.traceparent.as_deref(), Some(trace));
        }
        let agent = captured_env(&[("AI_AGENT", slug)]).unwrap();
        assert_eq!(agent.session_id, None);
        assert_eq!(agent.traceparent, None);
    }
}

#[test]
fn captured_new_harness_shapes_resolve_without_borrowing_unrelated_ids() {
    // Synthetic values preserve the relevant combinations in observed.json;
    // these fixtures do not claim to run the actual harnesses.
    struct Case {
        vars: &'static [(&'static str, &'static str)],
        id: AgentId,
        session: Option<&'static str>,
    }
    for case in [
        Case {
            vars: &[
                ("DSH_SHELL", "1"),
                ("DSH_SESSION_ID", "deepseek-session"),
                ("DSH_HOME", "/synthetic/dsh"),
            ],
            id: AgentId::DeepSeekHarness,
            session: Some("deepseek-session"),
        },
        Case {
            vars: &[
                ("AI_AGENT", "hermes-agent"),
                ("HERMES_AGENT", "true"),
                ("HERMES_SESSION_ID", "hermes-session"),
                ("HERMES_HOME", "/synthetic/hermes"),
            ],
            id: AgentId::Hermes,
            session: Some("hermes-session"),
        },
        Case {
            vars: &[
                ("JUNIE_SHIM_PATH", "/synthetic/junie-shim"),
                ("JUNIE_DATA", "/synthetic/junie"),
                ("MATTERHORN_SESSION_ID", "matterhorn-session"),
            ],
            id: AgentId::Junie,
            session: None,
        },
        Case {
            vars: &[
                ("KILO", "1"),
                ("OPENCODE", "1"),
                ("AGENT", "1"),
                ("KILO_RUN_ID", "kilo-run"),
            ],
            id: AgentId::KiloCode,
            session: None,
        },
        Case {
            vars: &[
                ("OPENCLAW_SHELL", "exec"),
                ("OPENCLAW_CLI", "1"),
                ("OPENCLAW_STATE_DIR", "/synthetic/openclaw"),
            ],
            id: AgentId::OpenClaw,
            session: None,
        },
        Case {
            vars: &[("VTCODE", "1"), ("VTCODE_TRUST_WORKSPACE", "full-auto")],
            id: AgentId::VTCode,
            session: None,
        },
    ] {
        let agent = captured_env(case.vars).unwrap();
        assert_eq!(agent.id, case.id);
        assert_eq!(agent.session_id.as_deref(), case.session, "{:?}", case.id);
    }
}

#[test]
fn captured_goose_and_cline_gaps_do_not_promote_ambiguous_ancestry() {
    // Goose adds only a generic session ID to its configured environment.
    assert!(
        captured_env(&[
            ("AGENT_SESSION_ID", "goose-session"),
            ("GOOSE_MODE", "auto"),
            ("GOOSE_MODEL", "example-model"),
            ("GOOSE_PROVIDER", "openai"),
            ("GOOSE_DISABLE_KEYRING", "1"),
        ])
        .is_none()
    );
    // Cline's agent and non-agent dependency child share these launch variables.
    assert!(
        captured_env(&[
            ("CLINE_WRAPPER_PATH", "/synthetic/cline/bin/cline"),
            (
                "CLINE_CONNECTOR_CLI_LAUNCH",
                r#"{"launcher":"/synthetic/cline","connectArgsPrefix":["connect"],"cwd":"/work"}"#
            ),
            ("NODE_EXTRA_CA_CERTS", "/synthetic/cline/certs.pem"),
        ])
        .is_none()
    );
}
