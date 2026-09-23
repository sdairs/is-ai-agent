# Detection audit against observed environments

This audit implements [issue #5](https://github.com/sdairs/is-ai-agent/issues/5)
against the sixteen environments in [observed.json](inventory/observed.json), as
committed in `0366705` on 23 September 2026. It replays the captured values through
`detect_with`, with filesystem detection disabled. It does not launch a new agent
or certify every version, operating system, IDE, PTY, SDK or session lifecycle.
The original live collection and its controls are described in [discovery.md](discovery.md).

The baseline is the 0.5.0 detector in `0366705`. Correct identities increase from
**8/16 to 14/16**. Hermes previously returned `Unknown`; Kilo returned OpenCode.
Six environments returned no match, of which four now have an approved rule.

| Captured harness | Before | After | Winning signal after refresh | Session source after refresh |
| --- | --- | --- | --- | --- |
| Claude Code | Claude Code | Claude Code | `AI_AGENT` | `CLAUDE_CODE_SESSION_ID` |
| Cline | None | None | — | — |
| Codex | Codex | Codex | `CODEX_THREAD_ID` | `CODEX_THREAD_ID` |
| Crush | Crush | Crush | `AGENT` | — |
| DeepSeek Harness | None | DeepSeek Harness | `DSH_SHELL=1` | `DSH_SESSION_ID` |
| Gemini CLI | Gemini CLI | Gemini CLI | `GEMINI_CLI` | — |
| GitHub Copilot | GitHub Copilot | GitHub Copilot | `COPILOT_AGENT_SESSION_ID` | `COPILOT_AGENT_SESSION_ID` |
| Goose | None | None | — | — |
| Hermes Agent | Unknown | Hermes Agent | `AI_AGENT` | `HERMES_SESSION_ID` |
| Junie | None | Junie | `JUNIE_SHIM_PATH` | — |
| Kilo Code | OpenCode | Kilo Code | `KILO=1` | — |
| OpenClaw | None | OpenClaw | `OPENCLAW_SHELL=exec` | — |
| OpenCode | OpenCode | OpenCode | `OPENCODE` | — |
| Pi | Pi | Pi | `AI_AGENT` | `PI_SESSION_ID` (new) |
| Qwen Code | Qwen Code | Qwen Code | `QWEN_CODE` | `QWEN_CODE_SESSION_ID` |
| VTCode | None | VTCode | `VTCODE=1` | — |

The new Claude child marker and Codex root-session fallback do not change these
rows' winning signals: a known generic identity still wins, and Codex still prefers
its existing thread marker. Isolated regression tests exercise the new fallbacks.
Codex's root and thread IDs happen to match in this capture, but only the thread
is exposed as `Agent.session_id`; root-only input has no session value.

## Decisions from the controls

- **Cline:** `CLINE_WRAPPER_PATH`, `CLINE_CONNECTOR_CLI_LAUNCH` and
  `NODE_EXTRA_CA_CERTS` also appear in a non-agent `cline skill list` child. They
  cannot distinguish agent commands on this surface. Existing Cline rules remain
  for compatibility; neither `CLINE_ACTIVE` nor `CLINE_TASK_ID` was captured.
- **Goose:** `GOOSE_PROVIDER`, `GOOSE_MODEL` and other configuration are inherited
  from the launcher. The added `AGENT_SESSION_ID` does not identify a product.
  Keep the gap and the existing `GOOSE_TERMINAL` compatibility rule. The request
  to restore specific markers is [Goose #12470](https://github.com/aaif-goose/goose/issues/12470).
- **Junie:** the issue explicitly approves shim attribution via a nonblank
  `JUNIE_SHIM_PATH`. This is launcher ancestry, not proof of a model-initiated
  command; the human interactive control remains unresolved. The newly observed
  `MATTERHORN_SESSION_ID` stays a research lead, outside the session API.
- **Kilo:** `KILO=1` must precede the inherited `OPENCODE=1`. Neither bare
  `AGENT=1` nor `KILO_RUN_ID` supplies a conversation identity.
- **DeepSeek:** a model/API key, profile or home directory cannot identify this
  harness. `DSH_SESSION_ID` alone is also available to the human Web UI terminal;
  require `DSH_SHELL=1` or an explicit generic identity before extracting it.

## Issue requirements outside this capture

Grok Build is the seventh new identity. It is absent from the inventory and is
supported by the vendor's [1.0.4 changelog](https://x.ai/build/changelog), which
documents `GROK_SESSION_ID` for tool commands and MCP servers. Its tests are
synthetic; no Grok Build live run is claimed. The legacy Grok CLI identity and
generic aliases remain separate.

The inventory cannot establish that every configuration variable is safe to
detect. Issue #5 removes `COPILOT_GITHUB_TOKEN`,
`COPILOT_MODEL`, `COPILOT_ALLOW_ALL`, `REPL_ID` and `GROK_AGENT` as automatic
signals; synthetic regression tests cover these exclusions. Blank and false
generic values are ignored without disabling other
detection. Other legacy rules are retained for compatibility and are not newly
certified by this audit.

`HERMES_SESSION_THREAD_ID`, `KILO_RUN_ID`, `MATTERHORN_SESSION_ID`, model/version
metadata and generic trace context are not new session sources. Qwen Live,
Muse Code and the other deferred products remain outside this refresh, as
specified by issue #5. No inventory values or collection rules are changed.

## Reproduce

```sh
python3 tests/harnesses/audit_detection.py --revision 0366705
python3 tests/harnesses/audit_detection.py
```

The audit requires Python 3.10+ and Rust supporting edition 2024. It compiles the
selected library source and an isolated lookup driver into a temporary directory.
Captured strings, including empty values and whitespace, are supplied unchanged;
the parent environment and filesystem cannot contribute detection signals. The
report contains identities, signal names and session-equality observations, not
raw values. `session_matches` lists equal captured values, not definitive source
selection: Codex's equal root/thread values illustrate the distinction.

The audit is observational and imposes no expected identity on future inventory
updates. Library regression cases in [tests/detect.rs](../detect.rs) use synthetic
inputs to enforce approved predicates, precedence and session semantics. Collection
continues to accept successfully verified harness execution even if detection
returns no match.
