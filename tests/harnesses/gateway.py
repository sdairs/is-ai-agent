"""Bounded mock / credential-isolating OpenAI chat-completions gateway.

Only this container sees the real endpoint and key. It never logs requests,
headers, upstream error bodies, or credentials. No redirects are followed.
"""
import json
import os
import re
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MODE = os.environ.get("GATEWAY_MODE", "mock")
BASE_URL = os.environ.get("INFERENCE_BASE_URL", "")
MODEL = os.environ.get("INFERENCE_MODEL", "")
TOKEN = Path("/run/secrets/inference_token").read_text().strip() if MODE == "live" else ""
if MODE == "live" and (not TOKEN or "\n" in TOKEN or "\r" in TOKEN):
    raise SystemExit("Invalid token file")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Handler(BaseHTTPRequestHandler):
    count = 0
    lock = threading.Lock()

    def log_message(self, *_):
        pass

    def error(self, status):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"error":{"message":"Harness gateway request failed"}}')

    def do_POST(self):
        with self.lock:
            Handler.count += 1
            count = Handler.count
        if self.path != "/v1/chat/completions" or count > 6:
            return self.error(429 if count > 6 else 404)
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 1024 * 1024:
                return self.error(413)
            body = json.loads(self.rfile.read(size))
            if MODE == "mock":
                return self.mock(body)
            body["model"] = MODEL
            # Bound generation independently of harness configuration.
            body.pop("max_completion_tokens", None)
            body["max_tokens"] = min(int(body.get("max_tokens", 2048)), 2048)
            request = urllib.request.Request(
                BASE_URL.rstrip("/") + "/chat/completions",
                json.dumps(body).encode(),
                {"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"},
            )
            with urllib.request.build_opener(NoRedirect).open(request, timeout=60) as response:
                self.send_response(200)
                self.send_header("Content-Type", response.headers.get("Content-Type", "text/event-stream"))
                self.end_headers()
                total = 0
                while line := response.readline(1024 * 1024):
                    total += len(line)
                    if total > 8 * 1024 * 1024:
                        break
                    self.wfile.write(line.replace(TOKEN.encode(), b"[REDACTED]"))
                    self.wfile.flush()
        except (ValueError, KeyError, TypeError, OSError, urllib.error.URLError):
            # Do not expose exception text: an upstream error may echo headers.
            self.close_connection = True

    def mock(self, body):
        messages = body["messages"]
        completed = any(m.get("role") == "tool" for m in messages)
        shell_tools = [t["function"] for t in body.get("tools", [])
                       if t.get("function", {}).get("name") in ("bash", "run_shell_command")]
        if completed or not shell_tools:
            delta = {"content": "Probe command completed."}
            reason = "stop"
        else:
            prompt = " ".join(str(m.get("content", "")) for m in messages if m.get("role") == "user")
            command = re.search(r"/usr/local/bin/agent-probe /artifacts/agent.json [0-9a-f]{32}", prompt)
            if not command:
                return self.error(400)
            tool = shell_tools[0]
            arguments = {"command": command[0]}
            if "description" in tool.get("parameters", {}).get("properties", {}):
                arguments["description"] = "Run detector probe"
            delta = {"tool_calls": [{"index": 0, "id": "call_probe", "type": "function", "function": {
                "name": tool["name"], "arguments": json.dumps(arguments),
            }}]}
            reason = "tool_calls"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream" if body.get("stream") else "application/json")
        self.end_headers()
        if not body.get("stream"):
            message = {"role": "assistant", "content": None, **delta}
            for call in message.get("tool_calls", []):
                call.pop("index", None)
            self.wfile.write(json.dumps({"id": "smoke", "object": "chat.completion", "created": 0,
                "model": "probe-model", "choices": [{"index": 0, "message": message, "finish_reason": reason}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}).encode())
            return
        for payload, finish in [({"role": "assistant"}, None), (delta, None), ({}, reason)]:
            chunk = {"id": "smoke", "object": "chat.completion.chunk", "created": 0, "model": "probe-model",
                     "choices": [{"index": 0, "delta": payload, "finish_reason": finish}]}
            self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
