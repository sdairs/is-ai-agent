"""Verify rejection of false evidence and credential handling, without a model."""
import io
import json
import unittest
from unittest.mock import patch

import gateway
import run


class EvidenceTests(unittest.TestCase):
    def events(self, command="probe", error=False, call_id="1", output='{"agent":"pi"}'):
        return "\n".join(json.dumps(event) for event in [
            {"type": "tool_execution_start", "toolName": "bash", "toolCallId": "1", "args": {"command": command}},
            {"type": "tool_execution_end", "toolCallId": call_id, "isError": error,
             "result": {"content": [{"type": "text", "text": output}]}},
            {"type": "agent_settled"},
        ])

    def test_matching_execution_and_artifact(self):
        self.assertTrue(all(run.verify_events(self.events(), "probe", {"agent": "pi"}).values()))

    def test_assistant_claim_is_not_execution(self):
        raw = json.dumps({"type": "message_end", "message": {"content": "Done!"}})
        self.assertFalse(run.verify_events(raw, "probe", {})["tool_completed"])

    def test_wrong_command_error_unrelated_end_or_changed_artifact_fails(self):
        for raw in [self.events(command="echo fake"), self.events(error=True),
                    self.events(call_id="unrelated"), self.events(output='{"agent":"codex"}'),
                    self.events() + "\n" + self.events()]:
            self.assertFalse(all(run.verify_events(raw, "probe", {"agent": "pi"}).values()))

    def test_stale_nonce_and_extra_fields_rejected(self):
        probe = {"schema": 2, "nonce": "new", "library_version": run.library_version(), "agent": "pi",
                 "signal": "AI_AGENT", "session_present": True,
                 "markers": {name: False for name in run.MARKERS},
                 "session_matches": {name: False for name in run.SESSIONS}}
        self.assertEqual(run.validate_probe(probe, "new"), probe)
        with self.assertRaises(ValueError):
            run.validate_probe(probe, "old")
        with self.assertRaises(ValueError):
            run.validate_probe({**probe, "token": "dummy-sensitive-value"}, "new")
        with self.assertRaises(ValueError):
            run.validate_probe({**probe, "markers": {**probe["markers"], "OPENCODE": "dummy-sensitive-value"}}, "new")

    def test_opencode_completion_is_correlated_to_command_and_output(self):
        def events(status="completed", command="probe", output='{"agent":"opencode"}', reason="stop"):
            return "\n".join(json.dumps(e) for e in [
                {"type": "tool_use", "part": {"tool": "bash", "state": {
                    "status": status, "input": {"command": command}, "output": output}}},
                {"type": "step_finish", "part": {"reason": reason}},
            ])
        for options in [{}, {"status": "error"}, {"command": "echo fake"}, {"output": "done"}, {"reason": "tool-calls"}]:
            checked = run.verify_events(events(**options), "probe", {"agent": "opencode"}, "opencode")
            self.assertEqual(all(checked.values()), not options)

    def test_qwen_requires_real_tool_result_not_assistant_text(self):
        def events(call_id="1", failed=False, output='Output: {"agent":"qwen-code"}'):
            return "\n".join(json.dumps(e) for e in [
                {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "1",
                    "name": "run_shell_command", "input": {"command": "probe"}}]}},
                {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": call_id,
                    "content": output, "is_error": failed}]}},
                {"type": "result", "subtype": "success", "is_error": False},
            ])
        for options in [{}, {"call_id": "wrong"}, {"failed": True}, {"output": "done"}]:
            checked = run.verify_events(events(**options), "probe", {"agent": "qwen-code"}, "qwen-code")
            self.assertEqual(all(checked.values()), not options)


class GatewayTests(unittest.TestCase):
    def handler(self, body=None):
        handler = gateway.Handler.__new__(gateway.Handler)
        data = json.dumps(body or {"messages": [], "max_tokens": 99999}).encode()
        handler.path = "/v1/chat/completions"
        handler.headers = {"Content-Length": str(len(data))}
        handler.rfile = io.BytesIO(data)
        handler.wfile = io.BytesIO()
        handler.send_response = lambda *_: None
        handler.send_header = lambda *_: None
        handler.end_headers = lambda: None
        gateway.Handler.count = 0
        return handler

    def test_token_is_only_in_upstream_auth_and_reflection_is_redacted(self):
        handler = self.handler()
        response = io.BytesIO(b'data: dummy-sensitive-value\n\n')
        response.headers = {"Content-Type": "text/event-stream"}
        with patch.object(gateway, "MODE", "live"), patch.object(gateway, "TOKEN", "dummy-sensitive-value"), \
             patch.object(gateway, "BASE_URL", "https://inference.invalid/v1"), patch.object(gateway, "MODEL", "test-model"), \
             patch.object(gateway.urllib.request, "build_opener") as opener:
            opener.return_value.open.return_value = response
            handler.do_POST()
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(request.get_header("Authorization"), "Bearer dummy-sensitive-value")
            self.assertEqual(json.loads(request.data)["max_tokens"], 2048)
            self.assertEqual(json.loads(request.data)["model"], "test-model")
            self.assertNotIn(b"dummy-sensitive-value", request.data)
            self.assertNotIn(b"dummy-sensitive-value", handler.wfile.getvalue())

    def test_upstream_error_detail_is_discarded(self):
        handler = self.handler()
        with patch.object(gateway, "MODE", "live"), patch.object(gateway, "BASE_URL", "https://inference.invalid/v1"), \
             patch.object(gateway.urllib.request, "build_opener") as opener:
            opener.return_value.open.side_effect = OSError("dummy-sensitive-value")
            handler.do_POST()
            self.assertNotIn(b"dummy-sensitive-value", handler.wfile.getvalue())

    def test_request_budget_and_redirect_rejection(self):
        handler = self.handler()
        gateway.Handler.count = 6
        statuses = []
        handler.send_response = statuses.append
        handler.do_POST()
        self.assertEqual(statuses, [429])
        self.assertIsNone(gateway.NoRedirect().redirect_request(None, None, 302, None, None, "https://other.invalid"))

    def test_mock_uses_advertised_shell_and_supports_both_response_formats(self):
        command = "/usr/local/bin/agent-probe /artifacts/agent.json " + "a" * 32
        for tool in ["bash", "run_shell_command"]:
            for stream in [True, False]:
                body = {"stream": stream, "messages": [{"role": "user", "content": command}],
                        "tools": [{"type": "function", "function": {"name": tool,
                            "parameters": {"properties": {"description": {"type": "string"}}}}}]}
                handler = self.handler(body)
                handler.do_POST()
                output = handler.wfile.getvalue().decode()
                if stream:
                    chunks = [json.loads(line[6:]) for line in output.split("\n") if line.startswith("data: {")]
                    call = chunks[1]["choices"][0]["delta"]["tool_calls"][0]
                else:
                    call = json.loads(output)["choices"][0]["message"]["tool_calls"][0]
                self.assertEqual(call["function"]["name"], tool)
                self.assertEqual(json.loads(call["function"]["arguments"])["command"], command)

    def test_mock_stops_after_tool_result(self):
        handler = self.handler({"messages": [{"role": "tool", "content": "probe output"}]})
        handler.do_POST()
        self.assertEqual(json.loads(handler.wfile.getvalue())["choices"][0]["finish_reason"], "stop")


if __name__ == "__main__":
    unittest.main()
