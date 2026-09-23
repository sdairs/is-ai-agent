// Configure the unmodified CLI. Never inject any detection/session marker.
import { mkdirSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const [harness, prompt, discoveryNonce] = process.argv.slice(2);
const env = { ...process.env, HOME: "/tmp", XDG_CONFIG_HOME: "/tmp/config",
  XDG_DATA_HOME: "/tmp/data", XDG_CACHE_HOME: "/tmp/cache", XDG_STATE_HOME: "/tmp/state" };
const write = (path, data) => writeFileSync(path, JSON.stringify(data));
let command, args;
if (harness === "pi") {
  mkdirSync("/tmp/pi", { recursive: true });
  write("/tmp/pi/models.json", { providers: { "harness-test": {
    baseUrl: "http://gateway:8080/v1", api: "openai-completions", apiKey: "not-a-secret",
    models: [{ id: "probe-model", reasoning: false, input: ["text"], contextWindow: 32768, maxTokens: 2048,
      compat: { supportsDeveloperRole: false, supportsStore: false } }],
  } } });
  write("/tmp/pi/settings.json", { retry: { enabled: false }, compaction: { enabled: false } });
  Object.assign(env, { PI_CODING_AGENT_DIR: "/tmp/pi", PI_TELEMETRY: "0", PI_OFFLINE: "1", PI_SKIP_VERSION_CHECK: "1" });
  command = "pi";
  args = ["--mode", "json", "--provider", "harness-test", "--model", "probe-model", "--thinking", "off",
    "--no-session", "--offline", "--no-extensions", "--no-skills", "--no-prompt-templates", "--no-themes",
    "--no-context-files", "--no-approve", "--tools", "bash", prompt];
} else if (harness === "qwen-code") {
  mkdirSync("/tmp/.qwen", { recursive: true });
  write("/tmp/.qwen/settings.json", {
    security: { auth: { selectedType: "openai" } },
    model: { name: "probe-model" }, general: { enableAutoUpdate: false, preventSystemSleep: false },
    privacy: { usageStatisticsEnabled: false }, telemetry: { enabled: false },
  });
  Object.assign(env, { OPENAI_API_KEY: "not-a-secret", OPENAI_BASE_URL: "http://gateway:8080/v1", OPENAI_MODEL: "probe-model" });
  command = "qwen";
  args = ["--output-format", "stream-json", "--yolo", "--max-session-turns", "4", "--prompt", prompt];
} else if (harness === "opencode") {
  mkdirSync("/tmp/config/opencode", { recursive: true });
  write("/tmp/config/opencode/opencode.json", {
    provider: { "harness-test": { npm: "@ai-sdk/openai-compatible", name: "Local test provider",
      options: { baseURL: "http://gateway:8080/v1", apiKey: "not-a-secret" },
      models: { "probe-model": { name: "Probe model", limit: { context: 32768, output: 2048 } } },
    } },
    model: "harness-test/probe-model", small_model: "harness-test/probe-model",
    share: "disabled", autoupdate: false, permission: { "*": "deny", bash: "allow", external_directory: "allow" },
  });
  Object.assign(env, { OPENCODE_DISABLE_AUTOUPDATE: "1", OPENCODE_DISABLE_MODELS_FETCH: "1",
    OPENCODE_DISABLE_PROJECT_CONFIG: "1", OPENCODE_DISABLE_AUTOCOMPACT: "1", OPENCODE_DISABLE_FFF: "1" });
  command = "opencode";
  args = ["run", "--format", "json", "--model", "harness-test/probe-model", prompt];
} else if (harness === "github-copilot") {
  Object.assign(env, { COPILOT_PROVIDER_BASE_URL: "http://gateway:8080/v1",
    COPILOT_PROVIDER_TYPE: "openai", COPILOT_PROVIDER_API_KEY: "not-a-secret", COPILOT_OFFLINE: "true" });
  command = "copilot";
  args = ["--model", "probe-model", "--allow-all-tools", "--allow-all-paths", "--no-ask-user",
    "--disable-builtin-mcps", "--no-auto-update", "--no-custom-instructions", "--output-format", "json", "-p", prompt];
} else if (harness === "crush") {
  mkdirSync("/tmp/config/crush", { recursive: true });
  write("/tmp/config/crush/crush.json", {
    providers: { "harness-test": { type: "openai-compat", base_url: "http://gateway:8080/v1", api_key: "not-a-secret",
      models: [{ id: "probe-model", name: "Probe model", context_window: 32768, default_max_tokens: 2048,
        cost_per_1m_in: 0, cost_per_1m_out: 0, cost_per_1m_in_cached: 0, cost_per_1m_out_cached: 0,
        can_reason: false, supports_attachments: false }], discover_models: false } },
    models: { large: { provider: "harness-test", model: "probe-model" }, small: { provider: "harness-test", model: "probe-model" } },
    options: { disable_provider_auto_update: true, disable_default_providers: true, disable_metrics: true,
      disable_auto_summarize: true, auto_lsp: false, data_directory: "/tmp/crush-data" },
  });
  Object.assign(env, { CRUSH_DISABLE_PROVIDER_AUTO_UPDATE: "1", CRUSH_DISABLE_METRICS: "1", DO_NOT_TRACK: "1" });
  command = "crush";
  args = ["run", "--quiet", prompt];
} else if (harness === "deepseek-harness") {
  Object.assign(env, { DSH_HOME: "/tmp/dsh", DSH_PERMISSION_MODE: "danger-full-access",
    DSH_TELEMETRY_MODE: "DISABLED", DSH_TOOLS_MODE: "native", OPENAI_API_KEY: "not-a-secret" });
  write("/tmp/dsh.patch.json", [
    { id: "llm-deepseek", disabled: true },
    { id: "session-log-deepseek", disabled: true },
    { id: "session-telemetry-otel", disabled: true },
    { id: "llm-pi-ai", config: { providers: { "harness-test": {
      apiKeyEnv: "OPENAI_API_KEY", api: "openai-completions", baseURL: "http://gateway:8080/v1",
      models: [{ id: "probe-model", contextWindow: 32768, maxTokens: 2048 }],
    } } } },
    { id: "agent-default-model", config: { provider: "harness-test", model: "probe-model" } },
  ]);
  command = "dsh";
  args = ["--profile", "headless", "--patch", "/tmp/dsh.patch.json", prompt];
} else if (harness === "kilo-code") {
  mkdirSync("/tmp/config/kilo", { recursive: true });
  write("/tmp/config/kilo/kilo.json", {
    provider: { "harness-test": { npm: "@ai-sdk/openai-compatible", name: "Local test provider",
      options: { baseURL: "http://gateway:8080/v1", apiKey: "not-a-secret" },
      models: { "probe-model": { name: "Probe model", limit: { context: 32768, output: 2048 } } },
    } },
    model: "harness-test/probe-model", small_model: "harness-test/probe-model",
    share: "disabled", autoupdate: false, permission: { "*": "deny", bash: "allow", external_directory: "allow" },
  });
  Object.assign(env, { KILO_DISABLE_AUTOUPDATE: "1", KILO_DISABLE_MODELS_FETCH: "1",
    OPENCODE_DISABLE_AUTOUPDATE: "1", OPENCODE_DISABLE_MODELS_FETCH: "1" });
  command = "kilo";
  args = ["run", "--format", "json", "--model", "harness-test/probe-model", prompt];
} else if (harness === "openclaw") {
  write("/tmp/openclaw.json", {
    models: { providers: { "harness-test": { baseUrl: "http://gateway:8080/v1", apiKey: "not-a-secret",
      api: "openai-completions", models: [{ id: "probe-model", name: "Probe model", reasoning: false,
        input: ["text"], contextWindow: 32768, maxTokens: 2048 }] } } },
    agents: { defaults: { model: { primary: "harness-test/probe-model" }, workspace: "/work" } },
  });
  command = "openclaw";
  args = ["agent", "exec", "--config", "/tmp/openclaw.json", "--cwd", "/work", "--code-mode", "direct", "--json", prompt];
} else if (harness === "junie") {
  Object.assign(env, { JUNIE_SKIP_UPDATE_CHECK: "1", JUNIE_DATA: "/opt/junie" });
  mkdirSync("/tmp/junie-models", { recursive: true });
  write("/tmp/junie-models/probe.json", { id: "probe-model", baseUrl: "http://gateway:8080/v1/chat/completions",
    apiType: "OpenAICompletion", apiKey: "not-a-secret", maxContextLength: 32768 });
  command = "junie";
  args = ["--skip-update-check", "--share-anonymous-statistics=false", "--model-location=/tmp/junie-models",
    "--model=custom:probe", "--output-format=json-stream", "--project=/work", prompt];
} else if (harness === "hermes-agent") {
  mkdirSync("/tmp/hermes", { recursive: true });
  write("/tmp/hermes/config.yaml", {
    model: { provider: "custom", default: "probe-model", base_url: "http://gateway:8080/v1" },
    terminal: { backend: "local", timeout: 30 }, compression: { enabled: false },
    memory: { memory_enabled: false, user_profile_enabled: false },
    auxiliary: { title_generation: { enabled: false } },
  });
  Object.assign(env, { HERMES_HOME: "/tmp/hermes", OPENAI_API_KEY: "not-a-secret",
    OPENAI_BASE_URL: "http://gateway:8080/v1", HERMES_YOLO_MODE: "true" });
  command = "hermes";
  args = ["chat", "--oneshot", "--provider", "custom", "--model", "probe-model",
    "--toolsets", "terminal", "--format", "stream-json", "-q", prompt];
} else if (harness === "vtcode") {
  writeFileSync("/tmp/vtcode.toml", `
default_primary_agent = "build"
[agent]
provider = "harness-test"
default_model = "probe-model"
api_key_env = "OPENAI_API_KEY"
[commands]
allow_list = ["/usr/local/bin/agent-probe"]
allow_glob = ["/usr/local/bin/agent-probe *"]
[agent.harness]
orchestration_mode = "single"
[agent.small_model]
enabled = false
[automation.full_auto]
enabled = true
require_profile_ack = false
max_turns = 4
[[custom_providers]]
name = "harness-test"
display_name = "Test provider"
base_url = "http://gateway:8080/v1"
api_key_env = "OPENAI_API_KEY"
models = ["probe-model"]
`);
  Object.assign(env, { OPENAI_API_KEY: "not-a-secret", VTCODE_TRUST_WORKSPACE: "full-auto" });
  command = "vtcode";
  args = ["exec", "--json", "--config", "/tmp/vtcode.toml", "--dangerously-skip-permissions", prompt];
} else if (harness === "goose") {
  Object.assign(env, { GOOSE_PROVIDER: "openai", GOOSE_MODEL: "probe-model", OPENAI_API_KEY: "not-a-secret",
    OPENAI_HOST: "http://gateway:8080", GOOSE_MODE: "auto", GOOSE_MAX_TURNS: "3", GOOSE_DISABLE_KEYRING: "1" });
  command = "goose";
  args = ["run", "--with-builtin", "developer", "--no-profile", "--output-format", "stream-json", "-t", prompt];
} else if (harness === "cline") {
  command = "cline";
  execFileSync(`/usr/local/bin/${command}`, ["auth", "--provider", "openai", "--apikey", "not-a-secret",
    "--modelid", "probe-model", "--baseurl", "http://gateway:8080/v1"], { env, stdio: "pipe" });
  args = ["--auto-approve", "true", "--json", "--timeout", "60", prompt];
} else if (harness === "codex") {
  mkdirSync("/tmp/.codex", { recursive: true });
  writeFileSync("/tmp/.codex/config.toml", `model = "gpt-5.4"
model_provider = "harness-test"
[model_providers.harness-test]
name = "Local test provider"
base_url = "http://gateway:8080/v1"
wire_api = "responses"
requires_openai_auth = false
`);
  command = "codex";
  args = ["exec", "--json", "--ephemeral", "--skip-git-repo-check", "--sandbox", "danger-full-access", prompt];
} else if (harness === "claude-code") {
  Object.assign(env, { ANTHROPIC_BASE_URL: "http://gateway:8080", ANTHROPIC_API_KEY: "not-a-secret",
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: "1", DISABLE_AUTOUPDATER: "1" });
  command = "claude";
  args = ["--bare", "--print", "--verbose", "--output-format", "stream-json", "--max-turns", "3",
    "--dangerously-skip-permissions", "--model", "claude-sonnet-4-6", prompt];
} else if (harness === "gemini-cli") {
  mkdirSync("/tmp/.gemini", { recursive: true });
  write("/tmp/.gemini/settings.json", { security: { auth: { selectedType: "gemini-api-key" } },
    telemetry: { enabled: false }, privacy: { usageStatisticsEnabled: false } });
  Object.assign(env, { GEMINI_API_KEY: "not-a-secret", GOOGLE_GEMINI_BASE_URL: "http://127.0.0.1:8080" });
  command = "gemini";
  args = ["--model", "gemini-2.5-flash", "--skip-trust", "--yolo", "--output-format", "stream-json", "--prompt", prompt];
} else {
  throw new Error("Unknown test harness");
}
// Replace the configuration launcher so the CLI owns the container process
// and Docker observes its real exit status, including internal relaunches.
if (discoveryNonce) {
  if (!/^[a-f0-9]{32}$/.test(discoveryNonce)) throw new Error("Invalid discovery nonce");
  // This baseline includes provider settings but precedes agent startup. It is
  // never mounted on the host, returned to the provider, or uploaded as evidence.
  writeFileSync("/tmp/probe-baseline.json", JSON.stringify(env), { mode: 0o600, flag: "wx" });
  execFileSync("/usr/local/bin/agent-probe", ["/artifacts/configured.json", discoveryNonce, "--discover"],
    { env, stdio: "pipe" });
  if (harness === "cline") {
    // Exercise a real non-agent CLI command. Replace only its npx dependency
    // with a probe: do not download skills@latest or alter Cline's code.
    mkdirSync("/tmp/probe-bin");
    writeFileSync("/tmp/probe-bin/npx", `#!/bin/sh
[ "$#" = 3 ] && [ "$1" = -y ] && [ "$2" = skills@latest ] && [ "$3" = list ] || exit 97
exec /usr/local/bin/agent-probe /artifacts/nonagent.json ${discoveryNonce} --discover
`, { mode: 0o755 });
    execFileSync("/usr/local/bin/cline", ["skill", "list"], {
      env: { ...env, PATH: `/tmp/probe-bin:${env.PATH}` }, stdio: "pipe",
    });
  }
}
process.execve(`/usr/local/bin/${command}`, [command, ...args], env);
