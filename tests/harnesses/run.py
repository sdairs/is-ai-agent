#!/usr/bin/env python3
"""Run unmodified agent CLIs against a local scripted provider in Docker."""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import releases

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HARNESS = json.loads((HERE / "harnesses.json").read_text())
GATEWAY_IMAGE = "python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea"
BUILD_FILES = ["Cargo.toml", "Cargo.lock", "src/lib.rs", "examples/detect.rs", "examples/probe.rs",
               "tests/harnesses/install.mjs", "tests/harnesses/Dockerfile", "tests/harnesses/entrypoint.mjs", "tests/harnesses/discover.mjs", "tests/harnesses/harnesses.json"]
MARKERS = {"PI_CODING_AGENT", "PI_SESSION_ID", "QWEN_CODE", "GEMINI_CLI",
           "QWEN_CODE_SESSION_ID", "OPENCODE", "OPENCODE_PID",
           "COPILOT_CLI", "COPILOT_AGENT", "COPILOT_AGENT_SESSION_ID", "CRUSH", "GOOSE_TERMINAL",
           "CLINE_ACTIVE", "CLINE_TASK_ID", "CODEX_THREAD_ID", "CODEX_SESSION_ID", "CODEX_SANDBOX",
           "CLAUDECODE", "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_SESSION_ID", "DSH_SHELL", "DSH_SESSION_ID", "KILO", "OPENCLAW_SHELL", "HERMES_AGENT", "HERMES_SESSION_ID", "VTCODE", "JUNIE_SHIM_PATH", "MATTERHORN_SESSION_ID"}
SESSIONS = {"PI_SESSION_ID", "QWEN_CODE_SESSION_ID", "COPILOT_AGENT_SESSION_ID", "CLINE_TASK_ID", "CODEX_THREAD_ID", "CLAUDE_CODE_SESSION_ID", "DSH_SESSION_ID", "HERMES_SESSION_ID"}
EXECUTABLES = {"agent-probe", "node", "bash", "sh", "dash", "zsh", "goose", "cline", "pi", "qwen",
               "opencode", "copilot", "crush", "codex", "claude", "gemini", "other", "unavailable"}


EXACT_MARKERS = {"DSH_SHELL", "KILO", "OPENCLAW_SHELL", "HERMES_AGENT", "VTCODE"}

def validate_discovery(value, nonce):
    if (not isinstance(value, dict) or set(value) != {"schema", "nonce", "environment", "ancestry"}
            or value["schema"] != 1 or value["nonce"] != nonce):
        raise ValueError("Invalid discovery artifact")
    environment = value["environment"]
    if not isinstance(environment, dict) or len(environment) > 256:
        raise ValueError("Invalid discovery environment")
    for name, info in environment.items():
        if (not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,95}", name) or not isinstance(info, dict)
                or set(info) != {"change", "nonblank"} or type(info["nonblank"]) is not bool
                or not isinstance(info["change"], str) or info["change"] not in {"added", "removed", "changed", "unchanged"}):
            raise ValueError("Invalid discovery fields")
    if (not isinstance(value["ancestry"], list) or not 1 <= len(value["ancestry"]) <= 16
            or any(not isinstance(name, str) or name not in EXECUTABLES for name in value["ancestry"])):
        raise ValueError("Invalid discovery ancestry")
    return value


def read_artifact(path, nonce, validator=validate_discovery):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32768:
        raise ValueError("Artifact missing or invalid")
    return validator(json.loads(path.read_text()), nonce)


def build_fingerprint():
    digest = hashlib.sha256()
    for relative in BUILD_FILES:
        digest.update(relative.encode() + b"\0" + build_input(relative) + b"\0")
    return digest.hexdigest()


def build_input(relative):
    if relative == "tests/harnesses/harnesses.json":
        return (json.dumps(HARNESS, sort_keys=True, indent=2) + "\n").encode()
    return (ROOT / relative).read_bytes()


def override_version(harness, version):
    HARNESS[harness] = releases.pinned_spec(HARNESS[harness], version)


def docker(*args, check=True, timeout=180):
    result = subprocess.run(["docker", *map(str, args)], capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        # Never echo container output by default. Only sanitized artifacts persist.
        raise RuntimeError("Docker command failed: " + str(args[0]))
    return result


def build(harness, image):
    # Explicit allowlist: .git, local secrets, research, and artifacts never enter
    # the build context, even if an unrelated .dockerignore changes later.
    with tempfile.TemporaryDirectory(prefix="agent-test-build-") as name:
        context = Path(name)
        for relative in BUILD_FILES:
            destination = context / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(build_input(relative))
        spec = HARNESS[harness]
        print(f"Building isolated {harness} {spec['version']} image...", flush=True)
        # Build contains no credentials; normal progress is useful for long pulls.
        subprocess.run(["docker", "build", "-f", str(context / "tests/harnesses/Dockerfile"),
                        "--label", "is-ai-agent.build-sha256=" + build_fingerprint(),
                        "--build-arg", "HARNESS_PACKAGE=" + spec["package"],
                        "--build-arg", "HARNESS_VERSION=" + spec["version"],
                        "-t", image, str(context)], check=True)


def validate_probe(value, nonce):
    keys = {"schema", "nonce", "library_version", "agent", "signal", "session_present", "markers", "exact_markers", "session_matches", "generic_markers"}
    if not isinstance(value, dict) or set(value) != keys or value["schema"] != 4 or value["nonce"] != nonce:
        raise ValueError("Invalid or stale probe artifact")
    if value["agent"] not in [None, "unknown", *HARNESS] or value["signal"] not in [None, "AGENT", "AI_AGENT", *MARKERS]:
        raise ValueError("Unexpected detector attribution")
    if type(value["session_present"]) is not bool:
        raise ValueError("Invalid session presence")
    for field, names in [("markers", MARKERS), ("exact_markers", EXACT_MARKERS), ("session_matches", SESSIONS)]:
        if not isinstance(value[field], dict) or set(value[field]) != names or any(type(v) is not bool for v in value[field].values()):
            raise ValueError("Invalid probe fields")
    if value["library_version"] != library_version():
        raise ValueError("Probe library version mismatch")
    validate_generic(value["generic_markers"])
    return value


def validate_generic(value):
    if (not isinstance(value, dict) or set(value) != {"AGENT", "AI_AGENT"}
            or any(v not in [None, "unknown", *HARNESS] for v in value.values())):
        raise ValueError("Invalid generic marker classification")
    return value


def library_version():
    return re.search(r'^version = "([^"]+)"', (ROOT / "Cargo.toml").read_text(), re.M)[1]


def output_matches(text, probe, depth=0):
    if depth > 8:
        return False
    if isinstance(text, (dict, list)):
        if text == probe:
            return True
        return any(output_matches(v, probe, depth + 1) for v in (text.values() if isinstance(text, dict) else text))
    if not isinstance(text, str):
        return False
    for line in text.split("\n"):
        try:
            value = json.JSONDecoder().raw_decode(line[line.index("{"):])[0]
            if output_matches(value, probe, depth + 1):
                return True
        except ValueError:
            pass
    return False


def verify_events(raw, command, probe, harness="pi"):
    events = [json.loads(line) for line in raw.split("\n") if line.strip()]
    if harness == "opencode":
        calls = [e["part"] for e in events if e.get("type") == "tool_use"]
        valid = len(calls) == 1 and calls[0].get("tool") == "bash" and calls[0].get("state", {}).get("input", {}).get("command") == command
        success = bool(valid and calls[0]["state"].get("status") == "completed")
        return {"exact_probe_command": bool(valid), "tool_completed": success,
                "tool_output_matches_artifact": success and output_matches(calls[0]["state"].get("output"), probe),
                "agent_settled": any(e.get("type") == "step_finish" and e.get("part", {}).get("reason") == "stop" for e in events)
                                 and not any(e.get("type") == "error" for e in events)}
    if harness == "qwen-code":
        calls = [b for e in events if e.get("type") == "assistant" for b in e.get("message", {}).get("content", [])
                 if isinstance(b, dict) and b.get("type") == "tool_use"]
        results = [b for e in events if e.get("type") == "user" for b in e.get("message", {}).get("content", [])
                   if isinstance(b, dict) and b.get("type") == "tool_result"]
        valid = len(calls) == 1 and calls[0].get("name") == "run_shell_command" and calls[0].get("input", {}).get("command") == command
        success = bool(valid and len(results) == 1 and results[0].get("tool_use_id") == calls[0].get("id") and not results[0].get("is_error", False))
        content = results[0].get("content", "") if success else ""
        if isinstance(content, list):
            content = "\n".join(b.get("text", "") for b in content if b.get("type") == "text")
        return {"exact_probe_command": bool(valid), "tool_completed": success,
                "tool_output_matches_artifact": success and output_matches(content, probe),
                "agent_settled": any(e.get("type") == "result" and e.get("subtype") == "success" and e.get("is_error") is False for e in events)}
    starts = [event for event in events if event.get("type") == "tool_execution_start"]
    valid = len(starts) == 1 and starts[0].get("toolName") == "bash" and starts[0].get("args", {}).get("command") == command
    ends = [event for event in events if event.get("type") == "tool_execution_end"]
    success = bool(valid and len(ends) == 1 and ends[0].get("toolCallId") == starts[0].get("toolCallId")
                   and ends[0].get("isError") is False)
    matched = False
    if success:
        for block in ends[0].get("result", {}).get("content", []):
            if block.get("type") != "text":
                continue
            matched |= output_matches(block.get("text", ""), probe)
    return {"exact_probe_command": bool(valid), "tool_completed": success,
            "tool_output_matches_artifact": matched,
            "agent_settled": any(e.get("type") == "agent_settled" for e in events)}


def verify_provider(evidence, command, probe, tool):
    calls, results = evidence.get("calls", []), evidence.get("results", [])
    valid = len(calls) == 1 and calls[0].get("command") == command and calls[0].get("name") == tool
    success = bool(valid and len(results) == 1 and results[0].get("id") == calls[0].get("id")
                   and results[0].get("is_error") is False)
    return {"exact_probe_command": bool(valid), "tool_completed": success,
            "tool_output_matches_artifact": success and output_matches(results[0].get("content"), probe),
            "agent_settled": evidence.get("final_responses", 0) > 0}


def classify_result(report, spec, expect_undetected=False):
    checks, probe = report["checks"], report["probe"]
    if expect_undetected:
        # A pinned known gap is an explicit observation, never a detection pass.
        # Do not accept tool failures, unexpected attribution, or new markers.
        markers_match = (checks.get("harness_exported_markers", False) if spec.get("known_gap_present_markers")
                         else not any(probe["markers"][name] for name in spec["markers"]))
        expected = (spec.get("known_gap") and checks["plain_shell_not_detected"]
                    and checks.get("configured_environment_not_detected", True)
                    and checks.get("non_agent_command_not_detected", True)
                    and checks["real_shell_tool_executed"] and probe["agent"] is None
                    and probe["signal"] is None and not probe["session_present"]
                    and markers_match)
        return "known-gap" if expected else "fail"
    return "pass" if all(checks.values()) else "fail"


def run(args):
    spec = HARNESS[args.harness]
    if args.discover and args.mode != "mock":
        raise ValueError("Discovery is restricted to credential-free mock mode")
    if args.expect_undetected and (not spec.get("known_gap") or args.mode != "mock"):
        raise ValueError("--expect-undetected only applies to documented mock-mode detection gaps")
    image = f"is-ai-agent-test-{args.harness}:{spec['version']}"
    token = None
    if args.mode == "live" and spec.get("evidence") == "provider":
        raise ValueError("This adapter currently supports mock mode only")
    if args.mode == "live":
        if not all([args.base_url, args.model, args.token_file]):
            raise ValueError("Live mode needs --base-url, --model, and --token-file")
        url = urlsplit(args.base_url)
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("Use an HTTPS base URL without credentials, query, or fragment")
        token = Path(args.token_file).expanduser().resolve()
        if token.is_relative_to(ROOT) or not token.is_file() or token.stat().st_mode & 0o077:
            raise ValueError("Token must be a private file (chmod 600) outside this repository")
        if "," in str(token):
            raise ValueError("Docker mount paths cannot contain commas")
    if not args.skip_build:
        build(args.harness, image)
    image_fingerprint = docker("image", "inspect", image, "--format",
                               '{{index .Config.Labels "is-ai-agent.build-sha256"}}').stdout.strip()
    if image_fingerprint != build_fingerprint():
        raise ValueError("Image is stale; run again without --skip-build")

    run_id = uuid.uuid4().hex
    prefix = "agent-test-" + run_id[:12]
    network, gateway, agent = prefix, prefix + "-gateway", prefix + "-" + args.harness
    output = ROOT / "target" / "harness-runs" / args.harness / run_id
    output.mkdir(parents=True, mode=0o700)
    harden = ["--cap-drop=ALL", "--security-opt=no-new-privileges", "--read-only",
              "--pids-limit=128", "--memory=2g", "--cpus=2", "--log-driver=none"]
    nonce = uuid.uuid4().hex
    command = f"/usr/local/bin/agent-probe /artifacts/agent.json {nonce}"
    if args.discover:
        command += " --discover"
    report = {"schema": 2, "mode": args.mode, "harness": args.harness, "harness_version": spec["version"],
              "timestamp": datetime.now(timezone.utc).isoformat(), "run_id": run_id,
              "scope": "Linux noninteractive CLI shell tool; no PTY, SDK, MCP, resume, or human-command coverage",
              "image_id": docker("image", "inspect", image, "--format", "{{.Id}}").stdout.strip(),
              "build_sha256": image_fingerprint,
              "gateway_image": GATEWAY_IMAGE,
              "gateway_source_sha256": hashlib.sha256((HERE / "gateway.py").read_bytes()).hexdigest(),
              "probe_source_sha256": hashlib.sha256((ROOT / "examples/probe.rs").read_bytes()).hexdigest(),
              "adapter_source_sha256": hashlib.sha256(b"".join((HERE / name).read_bytes() for name in
                  ("entrypoint.mjs", "discover.mjs", "gateway.py"))).hexdigest(),
              "platform": docker("image", "inspect", image, "--format", "{{.Os}}/{{.Architecture}}").stdout.strip(),
              "library_source_sha256": hashlib.sha256((ROOT / "src/lib.rs").read_bytes()).hexdigest()}
    try:
        report["stage"] = "gateway"
        docker("network", "create", "--internal", network)
        gw_args = ["create", "--name", gateway, *harden, "--network", network, "--network-alias", "gateway",
                   "--mount", f"type=bind,src={HERE / 'gateway.py'},dst=/gateway.py,readonly",
                   "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "GATEWAY_MODE=" + args.mode]
        if token:
            gw_args += ["--mount", f"type=bind,src={token},dst=/run/secrets/inference_token,readonly",
                        "-e", "INFERENCE_BASE_URL=" + args.base_url, "-e", "INFERENCE_MODEL=" + args.model]
        gw_args += [GATEWAY_IMAGE, "python", "/gateway.py"]
        docker(*gw_args)
        if token:
            # Only the gateway can reach the provider. The CLI stays on --internal.
            docker("network", "connect", "bridge", gateway)
        docker("start", gateway)
        for _ in range(30):
            ready = docker("exec", gateway, "python", "-c",
                           "import socket; socket.create_connection(('127.0.0.1',8080),1).close()", check=False)
            if ready.returncode == 0:
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("Gateway did not start")

        # Only disposable evidence directories are writable host mounts. The
        # agent has no source tree, Docker socket, host HOME, or credential file.
        with tempfile.TemporaryDirectory(prefix="agent-test-evidence-") as temp:
            scratch = Path(temp)
            control_dir, agent_dir = scratch / "control", scratch / "agent"
            for directory in (control_dir, agent_dir):
                directory.mkdir(mode=0o777)
                directory.chmod(0o777)  # container UID 1000 differs from macOS UID
            common = [*harden, "--tmpfs", "/tmp:rw,exec,nosuid,nodev,size=512m,mode=1777",
                      "--tmpfs", "/work:rw,nosuid,nodev,size=16m,mode=1777"]
            report["stage"] = "version"
            actual_version = docker("run", "--rm", *common, "--network=none", "-e", "HOME=/tmp", "--entrypoint", spec["executable"], image,
                                    "--version").stdout.strip()
            if not re.search(r"(?<![\d.])" + re.escape(spec.get("reported_version", spec["version"])) + r"(?!\d|\.\d)", actual_version):
                raise ValueError("Installed version differs from test target")
            report["stage"] = "control"
            control = docker("run", "--rm", *common, "--network=none",
                             "--mount", f"type=bind,src={control_dir},dst=/artifacts",
                             "--entrypoint", "/bin/bash", image, "-lc",
                             f"/usr/local/bin/agent-probe /artifacts/control.json {nonce}")
            control_record = validate_probe(json.loads(control.stdout), nonce)
            if json.loads((control_dir / "control.json").read_text()) != control_record:
                raise ValueError("Control file differs from process output")
            report["control"] = control_record
            docker("create", "--name", agent, *common, "--network", "container:" + gateway if args.harness == "gemini-cli" else network,
                   "--mount", f"type=bind,src={agent_dir},dst=/artifacts", image, args.harness,
                   "Run exactly this command once using the shell tool, then stop. Do not set any environment variables, "
                   "edit files, or run any other command: " + command, *([nonce] if args.discover else []))
            report["stage"] = "agent"
            result = docker("start", "--attach", agent, check=False, timeout=150)
            report["container_exit_code"] = int(docker("inspect", agent, "--format", "{{.State.ExitCode}}").stdout)
            report["stage"] = "artifact"
            artifact = agent_dir / "agent.json"
            if artifact.is_symlink() or not artifact.is_file() or artifact.stat().st_size > 4096:
                raise ValueError("Probe artifact missing or invalid")
            report["probe"] = validate_probe(json.loads(artifact.read_text()), nonce)
            report["stage"] = "events"
            if spec.get("evidence") == "provider":
                evidence = docker("exec", gateway, "python", "-c",
                    "import urllib.request; print(urllib.request.urlopen('http://localhost:8080/evidence').read().decode())").stdout
                report["execution"] = verify_provider(json.loads(evidence), command, report["probe"], spec["tool"])
            else:
                report["execution"] = verify_events(result.stdout, command, report["probe"], args.harness)
            if args.discover:
                report["configured_control"] = read_artifact(agent_dir / "configured.json", nonce, validate_probe)
                report["discovery"] = {
                    "configured": read_artifact(agent_dir / "configured.json.discovery.json", nonce),
                    "agent": read_artifact(agent_dir / "agent.json.discovery.json", nonce),
                }
                if spec.get("evidence") == "provider":
                    observed = verify_provider(json.loads(evidence), command, report["discovery"]["agent"], spec["tool"])
                else:
                    observed = verify_events(result.stdout, command, report["discovery"]["agent"], args.harness)
                report["execution"]["discovery_matches_tool_output"] = all(observed.values())
                if args.harness == "cline":
                    report["non_agent_control"] = read_artifact(agent_dir / "nonagent.json", nonce, validate_probe)
                    report["discovery"]["non_agent"] = read_artifact(agent_dir / "nonagent.json.discovery.json", nonce)
                    report["discovery"]["non_agent_surface"] = "cline skill list; npx dependency replaced by argument-checking probe; no agent turn"

        p = report["probe"]
        report["checks"] = {
            "plain_shell_not_detected": control_record["agent"] is None,
            "real_shell_tool_executed": all(report["execution"].values()) and report["container_exit_code"] == 0,
            "harness_identified": p["agent"] == args.harness,
            "harness_exported_markers": all(p["markers"][name] and (name not in EXACT_MARKERS or p["exact_markers"][name]) for name in spec["markers"]),
            "session_contract": p["session_matches"][spec["session_var"]] if spec["session_var"] else not p["session_present"],
        }
        if args.discover:
            report["checks"]["configured_environment_not_detected"] = report["configured_control"]["agent"] is None
            if "non_agent_control" in report:
                report["checks"]["non_agent_command_not_detected"] = report["non_agent_control"]["agent"] is None
        report["status"] = classify_result(report, spec, args.expect_undetected)
        if spec.get("known_gap"):
            report["known_gap"] = spec["known_gap"]
        report["stage"] = "complete"
    except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as error:
        # Exception details could contain arbitrary harness text. Persist type only.
        report["status"] = "error"
        report["error_type"] = type(error).__name__
    finally:
        for name in (agent, gateway):
            docker("rm", "--force", name, check=False)
        docker("network", "rm", network, check=False)
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    for key in ("control", "probe", "configured_control", "non_agent_control", "discovery"):
        if key in report:
            (output / (key + ".json")).write_text(json.dumps(report[key], indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print("Report: " + str(output / "report.json"))
    return 0 if report["status"] in ("pass", "known-gap") else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", choices=list(HARNESS), default="pi")
    parser.add_argument("--mode", choices=["mock", "live"], default="mock")
    parser.add_argument("--base-url")
    parser.add_argument("--model")
    parser.add_argument("--token-file")
    parser.add_argument("--expect-undetected", action="store_true", help="Assert a documented missing-detection result; execution must still succeed")
    parser.add_argument("--skip-build", action="store_true", help="Use an already-built image for unchanged source")
    parser.add_argument("--discover", action="store_true", help="Compare configured and tool environments without exporting values (mock only)")
    parser.add_argument("--version", help="Select a reviewed version or trial an exact npm release without changing the manifest")
    args = parser.parse_args()
    if args.version:
        override_version(args.harness, args.version)
    raise SystemExit(run(args))
