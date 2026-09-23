// Public, version-pinned packages only. This runs during the isolated build.
import { readFileSync, writeFileSync, unlinkSync } from "node:fs";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
const [pkg, version] = process.argv.slice(2);
if (pkg === "goose") {
  const spec = JSON.parse(readFileSync("/opt/harnesses.json")).goose;
  const asset = spec.assets[process.arch];
  if (!asset || version !== spec.version) throw new Error("Unsupported Goose build");
  const url = `https://github.com/aaif-goose/goose/releases/download/v${version}/goose-${asset.arch}-unknown-linux-musl.tar.gz`;
  const response = await fetch(url);
  if (!response.ok) throw new Error("Goose download failed");
  const data = Buffer.from(await response.arrayBuffer());
  if (createHash("sha256").update(data).digest("hex") !== asset.sha256) throw new Error("Goose checksum mismatch");
  writeFileSync("/tmp/goose.tar.gz", data);
  execFileSync("tar", ["xzf", "/tmp/goose.tar.gz", "-C", "/usr/local/bin"]);
  unlinkSync("/tmp/goose.tar.gz");
} else {
  execFileSync("npm", ["install", "--global", `${pkg}@${version}`], { stdio: "inherit" });
  execFileSync("npm", ["cache", "clean", "--force"], { stdio: "inherit" });
}
