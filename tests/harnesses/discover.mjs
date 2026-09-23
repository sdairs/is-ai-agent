// Mock-only discovery. Preserve exact values from the isolated test environment.
import { readFileSync, readlinkSync, writeFileSync } from "node:fs";
import { basename } from "node:path";
import { fileURLToPath } from "node:url";

const validName = /^[A-Za-z_][A-Za-z0-9_]{0,95}$/;
const executables = new Set(["agent-probe", "node", "bash", "sh", "dash", "zsh",
  "goose", "cline", "pi", "qwen", "opencode", "copilot", "crush", "codex", "claude", "gemini"]);

export function compareEnvironment(before, after) {
  return Object.fromEntries([...new Set([...Object.keys(before), ...Object.keys(after)])]
    .filter(name => validName.test(name)).sort().map(name => [name, {
      change: !(name in before) ? "added" : !(name in after) ? "removed"
        : before[name] === after[name] ? "unchanged" : "changed",
      nonblank: typeof after[name] === "string" && after[name].trim().length > 0,
      value: Object.hasOwn(after, name) ? after[name] : null,
    }]));
}

export function ancestry(start) {
  const result = [], visited = new Set();
  let pid = start;
  while (pid > 0 && result.length < 16 && !visited.has(pid)) {
    visited.add(pid);
    try {
      const executable = basename(readlinkSync(`/proc/${pid}/exe`));
      result.push(executables.has(executable) ? executable : "other");
      pid = Number(readFileSync(`/proc/${pid}/status`, "utf8").match(/^PPid:\s+(\d+)/m)?.[1] || 0);
    } catch { result.push("unavailable"); break; }
  }
  return result;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [destination, nonce] = process.argv.slice(2);
  if (process.argv.length !== 4 || !/^[a-f0-9]{32}$/.test(nonce)) throw new Error("Invalid discovery arguments");
  const before = JSON.parse(readFileSync("/tmp/probe-baseline.json", "utf8"));
  const record = { schema: 3, nonce, environment: compareEnvironment(before, process.env),
    // Start at the Rust probe. The helper's own Node process is excluded.
    ancestry: ancestry(process.ppid) };
  const text = JSON.stringify(record) + "\n";
  // Probe output must be readable by the host runner's different UID on
  // Linux. Its host parent is private; the raw tmpfs baseline stays mode 0600.
  writeFileSync(destination, text, { flag: "wx", mode: 0o644 });
  process.stdout.write(text);
}
