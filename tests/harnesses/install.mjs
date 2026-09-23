// Public, version-pinned packages only. This runs during the isolated build.
import { readFileSync, writeFileSync, unlinkSync, mkdirSync, cpSync, chmodSync, symlinkSync } from "node:fs";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
const [pkg, version] = process.argv.slice(2);
const manifest = JSON.parse(readFileSync("/opt/harnesses.json"));
if (pkg === "vtcode" || pkg === "hermes-agent") {
  const spec = manifest[pkg];
  const asset = pkg === "vtcode" ? spec.assets[process.arch] : spec.source;
  if (!asset || version !== spec.version) throw new Error("Unsupported release build");
  const response = await fetch(asset.url);
  if (!response.ok) throw new Error("Release download failed");
  const data = Buffer.from(await response.arrayBuffer());
  if (createHash("sha256").update(data).digest("hex") !== asset.sha256) throw new Error("Release checksum mismatch");
  writeFileSync("/tmp/release.tar.gz", data);
  mkdirSync(`/opt/${pkg}`, { recursive: true });
  execFileSync("tar", ["xzf", "/tmp/release.tar.gz", "--strip-components=1", "-C", `/opt/${pkg}`]);
  unlinkSync("/tmp/release.tar.gz");
  if (pkg === "vtcode") {
    symlinkSync("/opt/vtcode/vtcode", "/usr/local/bin/vtcode");
  } else {
    execFileSync("apt-get", ["update"], { stdio: "inherit" });
    execFileSync("apt-get", ["install", "-y", "--no-install-recommends", "python3", "python3-venv", "git"], { stdio: "inherit" });
    execFileSync("python3", ["-m", "venv", "/opt/hermes-venv"]);
    execFileSync("/opt/hermes-venv/bin/pip", ["install", "--no-cache-dir", "-e", "/opt/hermes-agent"], { stdio: "inherit" });
    symlinkSync("/opt/hermes-venv/bin/hermes", "/usr/local/bin/hermes");
  }
} else if (pkg === "goose") {
  const spec = JSON.parse(readFileSync("/opt/harnesses.json")).goose;
  const asset = spec.assets[process.arch];
  if (!asset || version !== spec.version) throw new Error("Unsupported Goose build");
  const url = asset.url ?? `https://github.com/aaif-goose/goose/releases/download/v${version}/goose-${asset.arch}-unknown-linux-musl.tar.gz`;
  const response = await fetch(url);
  if (!response.ok) throw new Error("Goose download failed");
  const data = Buffer.from(await response.arrayBuffer());
  if (createHash("sha256").update(data).digest("hex") !== asset.sha256) throw new Error("Goose checksum mismatch");
  writeFileSync("/tmp/goose.tar.gz", data);
  execFileSync("tar", ["xzf", "/tmp/goose.tar.gz", "-C", "/usr/local/bin"]);
  unlinkSync("/tmp/goose.tar.gz");
} else {
  const spec = Object.values(manifest).find(s => s.package === pkg && s.version === version);
  if (spec?.npm_integrity) {
    const integrity = JSON.parse(execFileSync("npm", ["view", `${pkg}@${version}`, "dist.integrity", "--json"], { encoding: "utf8" }));
    if (integrity !== spec.npm_integrity) throw new Error("Resolved npm release integrity changed");
  }
  execFileSync("npm", ["install", "--global", `${pkg}@${version}`], { stdio: "inherit" });
  execFileSync("npm", ["cache", "clean", "--force"], { stdio: "inherit" });
  if (pkg === "@jetbrains/junie") {
    execFileSync("usermod", ["--home", "/tmp", "node"]);
    cpSync("/root/.local/share/junie", "/opt/junie", { recursive: true });
    cpSync("/root/.local/bin/junie", "/opt/junie-shim");
    chmodSync("/opt/junie-shim", 0o755);
    unlinkSync("/usr/local/bin/junie");
    writeFileSync("/usr/local/bin/junie", '#!/bin/sh\nexport JUNIE_DATA=/opt/junie\nexec /opt/junie-shim "$@"\n', { mode: 0o755 });
  }
}
