"""Scripted Chat Completions, Responses, Messages and Gemini endpoints.

Optional live Chat Completions: only this container sees the real endpoint and key. It never logs requests,
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
    evidence = {"calls": [], "results": [], "final_responses": 0}

    def do_GET(self):
        if MODE != "mock" or self.path != "/evidence":
            return self.error(404)
        self.json_response(self.evidence)

    def json_response(self, value):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(value).encode())

    def stream_response(self, events, named=False, done=False):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for event in events:
            prefix = "event: " + event["type"] + "\n" if named else ""
            self.wfile.write((prefix + "data: " + json.dumps(event) + "\n\n").encode())
        if done:
            self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


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
        path = self.path.split("?", 1)[0]
        allowed = path in ("/v1/chat/completions", "/v1/responses", "/v1/messages") or path.endswith(":streamGenerateContent") or path.endswith(":generateContent")
        if not allowed or (MODE == "live" and path != "/v1/chat/completions") or count > 6:
            return self.error(429 if count > 6 else 404)
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 1024 * 1024:
                return self.error(413)
            body = json.loads(self.rfile.read(size))
            if MODE == "mock":
                if path == "/v1/responses":
                    return self.mock_responses(body)
                if path == "/v1/messages":
                    return self.anthropic(body)
                if ":" in path:
                    return self.gemini(body)
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
        self.observe_chat(body)
        messages = body["messages"]
        completed = any(m.get("role") == "tool" for m in messages)
        shell_tools = [t["function"] for t in body.get("tools", [])
                       if self.is_shell(t.get("function", {}).get("name", ""))]
        submit = next((t["function"] for t in body.get("tools", [])
                       if t.get("function", {}).get("name") == "submit"), None)
        if completed or not shell_tools:
            delta = {"content": "Probe command completed."}
            reason = "stop"
            if completed:
                self.evidence["final_responses"] += 1
                # Junie's normal completion protocol requires its submit tool.
                # This does not execute a command or supply detection markers.
                if submit and "solution_summary" in submit.get("parameters", {}).get("properties", {}):
                    delta = {"tool_calls": [{"index": 0, "id": "finishprobe", "type": "function", "function": {
                        "name": "submit", "arguments": json.dumps({"solution_summary":
                            "### Summary\n- Ran detector probe.\n### Changes\n- Created probe artifact.\n### Verification\n- Command returned its result."}),
                    }}]}
                    reason = "tool_calls"
        else:
            prompt = " ".join(str(m.get("content", "")) for m in messages if m.get("role") == "user")
            command = re.search(r"/usr/local/bin/agent-probe /artifacts/agent.json [0-9a-f]{32}(?: --discover)?", prompt)
            if not command:
                return self.error(400)
            tool = shell_tools[0]
            arguments = self.arguments(tool, command[0])
            self.record_call(tool["name"], command[0])
            delta = {"tool_calls": [{"index": 0, "id": "callprobe", "type": "function", "function": {
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

    @staticmethod
    def is_shell(name):
        return name in ("bash", "Bash", "run_shell_command", "execute_command", "exec_command", "shell", "shell_command", "run_command", "run_commands", "developer__shell", "exec", "terminal", "unified_exec")

    @staticmethod
    def arguments(tool, command):
        schema = tool.get("parameters", tool.get("input_schema", {}))
        props = schema.get("properties", {})
        key = next((k for k in ("command", "cmd", "command_line") if k in props), "command")
        if "commands" in props:
            return {"commands": [command]}
        args = {key: ["/bin/bash", "-lc", command] if props.get(key, {}).get("type") == "array" else command}
        if "description" in props:
            args["description"] = "Run detector probe"
        if "requires_approval" in props:
            args["requires_approval"] = False
        return args

    def record_call(self, name, command):
        self.evidence["calls"].append({"id": "callprobe", "name": name, "command": command})

    def record_result(self, call_id, content, error=False):
        if isinstance(content, list):
            content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
        elif not isinstance(content, str):
            content = json.dumps(content)
        result = {"id": call_id, "content": content, "is_error": bool(error)}
        if result not in self.evidence["results"]:
            self.evidence["results"].append(result)

    def observe_chat(self, body):
        for m in body.get("messages", []):
            if m.get("role") == "tool":
                self.record_result(m.get("tool_call_id"), m.get("content"), m.get("is_error", False))

    def select(self, tools, prompt):
        tool = next((t for t in tools if self.is_shell(t.get("name", ""))), None)
        command = re.search(r"/usr/local/bin/agent-probe /artifacts/agent.json [0-9a-f]{32}(?: --discover)?", json.dumps(prompt))
        if not tool or not command:
            return None
        self.record_call(tool["name"], command[0])
        return tool["name"], self.arguments(tool, command[0])

    def anthropic(self, body):
        completed = False
        for m in body.get("messages", []):
            content = m.get("content", [])
            if isinstance(content, list):
                for part in content:
                    if part.get("type") == "tool_result":
                        completed = True
                        self.record_result(part.get("tool_use_id"), part.get("content"), part.get("is_error", False))
        selected = None if completed else self.select(body.get("tools", []), body.get("messages", []))
        if completed:
            self.evidence["final_responses"] += 1
        block = {"type": "tool_use", "id": "callprobe", "name": selected[0], "input": selected[1]} if selected else {"type": "text", "text": "Probe command completed."}
        reason = "tool_use" if selected else "end_turn"
        message = {"id": "msg_probe", "type": "message", "role": "assistant", "model": body.get("model"),
                   "content": [block], "stop_reason": reason, "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}}
        if not body.get("stream"):
            return self.json_response(message)
        start = {**message, "content": [], "stop_reason": None}
        empty = {**block, "input": {}} if selected else {"type": "text", "text": ""}
        delta = {"type": "input_json_delta", "partial_json": json.dumps(selected[1])} if selected else {"type": "text_delta", "text": block["text"]}
        self.stream_response([
            {"type": "message_start", "message": start},
            {"type": "content_block_start", "index": 0, "content_block": empty},
            {"type": "content_block_delta", "index": 0, "delta": delta},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_delta", "delta": {"stop_reason": reason, "stop_sequence": None}, "usage": {"output_tokens": 1}},
            {"type": "message_stop"},
        ], named=True)

    def mock_responses(self, body):
        completed = False
        for item in body.get("input", []):
            if isinstance(item, dict) and item.get("type") == "function_call_output":
                completed = True
                self.record_result(item.get("call_id"), item.get("output"))
        tools = []
        for t in body.get("tools", []):
            tools.extend(t.get("tools", []) if t.get("type") == "namespace" else [t])
        selected = None if completed else self.select(tools, body.get("input", []))
        if completed:
            self.evidence["final_responses"] += 1
        item = {"type": "function_call", "id": "fc_probe", "call_id": "callprobe", "name": selected[0],
                "arguments": json.dumps(selected[1]), "status": "completed"} if selected else {
                "type": "message", "id": "msg_probe", "role": "assistant", "status": "completed",
                "content": [{"type": "output_text", "text": "Probe command completed.", "annotations": []}]}
        response = {"id": "resp_done" if completed else "resp_probe", "object": "response", "created_at": 0,
                    "status": "completed", "output": [item], "model": body.get("model"),
                    "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}}
        if not body.get("stream"):
            return self.json_response(response)
        self.stream_response([
            {"type": "response.created", "response": {**response, "status": "in_progress", "output": []}},
            {"type": "response.output_item.added", "output_index": 0, "item": {**item, "status": "in_progress"}},
            {"type": "response.output_item.done", "output_index": 0, "item": item},
            {"type": "response.completed", "response": response},
        ], named=True)

    def gemini(self, body):
        completed = False
        for m in body.get("contents", []):
            for part in m.get("parts", []):
                if "functionResponse" in part:
                    completed = True
                    result = part["functionResponse"]
                    self.record_result(result.get("id", "callprobe"), result.get("response"), bool(result.get("response", {}).get("error")))
        tools = [t for group in body.get("tools", []) for t in group.get("functionDeclarations", [])]
        selected = None if completed else self.select(tools, body.get("contents", []))
        if completed:
            self.evidence["final_responses"] += 1
        part = {"functionCall": {"name": selected[0], "args": selected[1], "id": "callprobe"}} if selected else {"text": "Probe command completed."}
        response = {"candidates": [{"content": {"role": "model", "parts": [part]}, "finishReason": "STOP", "index": 0}],
                    "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1, "totalTokenCount": 2}, "modelVersion": "gemini-2.5-flash"}
        if ":streamGenerateContent" in self.path:
            self.stream_response([response])
        else:
            self.json_response(response)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
