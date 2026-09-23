# Release notes

## Unreleased — September 2026 detection refresh

This refresh audits detection against the [captured harness environments](tests/harnesses/inventory/observed.json) and the scoped evidence in [issue #5](https://github.com/sdairs/is-ai-agent/issues/5).

- Add DeepSeek Harness (`deepseek-harness`, `dsh`), Hermes Agent (`hermes-agent`, `hermes`), OpenClaw (`openclaw`), Grok Build (`grok-build`), Kilo Code (`kilo-code`, `kilo`, `kilocode`), Junie (`junie`), and VTCode (`vtcode`). Add the whole-value `github_copilot_app_agent` alias for GitHub Copilot.
- Use exact, case-sensitive values for `DSH_SHELL=1`, `HERMES_AGENT=true`, `OPENCLAW_SHELL=exec`, `KILO=1`, `VTCODE=1`, and the new Claude Code marker `CLAUDE_CODE_CHILD_SESSION=1`. Require nonblank `JUNIE_SHIM_PATH` and session-based identity fallbacks. Opaque accepted IDs and paths are preserved unchanged.
- Ignore blank generic values and trimmed, case-insensitive `0`, `false`, `no`, and `off`. These values skip that variable rather than disabling detection. Unknown names and bare true values remain `Unknown` fallbacks below specific signals.
- Remove detection based on `COPILOT_GITHUB_TOKEN`, `COPILOT_MODEL`, `COPILOT_ALLOW_ALL`, bare `REPL_ID`, and bare `GROK_AGENT`. This removes selected configuration/workspace false positives and prevents the Copilot token from becoming a matched signal in public/debug output. Replit and legacy Grok CLI generic aliases remain available; Grok Build has its own identity.
- Preserve known-name generic precedence (`AGENT` before `AI_AGENT`), whole-name matching before version/suffix parsing, Cowork refinement, and Amp/CodeBuddy before Claude and Qwen/veCLI before Gemini. Kilo now wins over its inherited OpenCode markers.
- Add nonblank `CODEX_SESSION_ID` as identity evidence only. `Agent.session_id` remains sourced exclusively from `CODEX_THREAD_ID` for Codex: a root ID alone returns `None`, and a thread ID wins when both exist. Add session extraction for DeepSeek Harness, Hermes Agent, Grok Build, and Pi. Do not substitute PTY, process-run, messaging-thread, or trace IDs.
- Clarify inherited-marker attribution, absence limits, Claude session lifecycle, and Claude/Qwen trace propagation. Claude's extra propagation flag is needed with a custom `ANTHROPIC_BASE_URL`, not unconditionally for the direct route.

The inventory contains controlled command-tool observations for six of the seven new identities; Grok Build is backed by its [vendor changelog](https://x.ai/build/changelog), not a live inventory probe. Cline and Goose remain detection gaps because the observed alternatives do not distinguish agent execution from controls. Junie attribution is scoped to its shim launcher. See the [discovery evidence](tests/harnesses/discovery.md) for platform, version and control limits.

Other legacy rules remain unchanged and require separate review. The public result shape and dependency-free environment/filesystem approach are preserved. This work does not certify all harness versions or add model/version metadata, a root-session field, process ancestry, confidence scores, or multi-match reporting.
