// Configure the unmodified CLI. Never inject any detection/session marker.
import { mkdirSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const [harness, prompt] = process.argv.slice(2);
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
process.execve(`/usr/local/bin/${command}`, [command, ...args], env);
