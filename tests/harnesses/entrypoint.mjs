// Configure the unmodified CLI. Never inject any detection/session marker.
import { mkdirSync, writeFileSync } from "node:fs";

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
} else {
  throw new Error("Unknown test harness");
}
// Replace the configuration launcher so the CLI owns the container process
// and Docker observes its real exit status, including internal relaunches.
process.execve(`/usr/local/bin/${command}`, [command, ...args], env);
