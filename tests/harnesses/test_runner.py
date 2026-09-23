"""Verify real-tool evidence and exact environment collection without a model."""
import io
import json
import subprocess
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import gateway
import run
import compare


class VersionWorkflowTests(unittest.TestCase):
    def test_trial_version_changes_build_input_without_editing_manifest(self):
        original = (run.HERE / "harnesses.json").read_bytes()
        with patch.dict(run.HARNESS, run.HARNESS.copy()):
            before = run.build_fingerprint()
            run.override_version("qwen-code", "0.24.3")
            self.assertNotEqual(before, run.build_fingerprint())
            self.assertEqual(json.loads(run.build_input("tests/harnesses/harnesses.json"))["qwen-code"]["version"], "0.24.3")
            self.assertEqual(original, (run.HERE / "harnesses.json").read_bytes())
            for version in ["latest", "^0.24.3", "0.24.3;echo bad"]:
                with self.assertRaises(ValueError):
                    run.override_version("qwen-code", version)
            with self.assertRaises(ValueError):
                run.override_version("goose", "9999.0.0")

    def test_comparison_requires_execution_and_valid_report_schema(self):
        record = {"harness": "qwen-code", "platform": "linux/amd64", "stage": "complete",
                  "checks": {"real_shell_tool_executed": True},
                  "probe": {"agent": "qwen-code", "signal": "QWEN_CODE", "nonce": "fresh",
                            "markers": {"QWEN_CODE": True}},
                  "discovery": {"agent": {"schema": 1, "nonce": "fresh", "ancestry": ["node"],
                                           "environment": {"QWEN_CODE": {"change": "added", "nonblank": True}}}}}
        changed = json.loads(json.dumps(record))
        self.assertEqual(compare.compare(record, changed), {})
        changed["probe"]["markers"]["QWEN_CODE"] = False
        self.assertEqual(compare.compare(record, changed), {"markers.QWEN_CODE": {"before": True, "after": False}})
        changed["checks"]["real_shell_tool_executed"] = False
        with self.assertRaises(ValueError):
            compare.compare(record, changed)
        changed = json.loads(json.dumps(record))
        changed["discovery"]["agent"]["environment"]["QWEN_CODE"]["value"] = "sentinel-secret"
        with self.assertRaises(ValueError):
            compare.compare(record, changed)


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
        probe = {"schema": 4, "nonce": "new", "library_version": run.library_version(), "agent": "pi",
                 "signal": "AI_AGENT", "session_present": True,
                 "markers": {name: False for name in run.MARKERS},
                 "exact_markers": {name: False for name in run.EXACT_MARKERS},
                 "session_matches": {name: False for name in run.SESSIONS},
                 "generic_markers": {"AGENT": None, "AI_AGENT": "pi"}}
        self.assertEqual(run.validate_probe(probe, "new"), probe)
        with self.assertRaises(ValueError):
            run.validate_probe(probe, "old")
        with self.assertRaises(ValueError):
            run.validate_probe({**probe, "token": "dummy-sensitive-value"}, "new")
        with self.assertRaises(ValueError):
            run.validate_probe({**probe, "markers": {**probe["markers"], "OPENCODE": "dummy-sensitive-value"}}, "new")
        with self.assertRaises(ValueError):
            run.validate_probe({**probe, "generic_markers": {"AGENT": "sentinel-secret", "AI_AGENT": None}}, "new")

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


class DiscoveryTests(unittest.TestCase):
    def test_environment_diff_keeps_exact_mock_values(self):
        before = {"SAME": "unchanged value", "CHANGED": "old value", "REMOVED": "gone"}
        after = {"SAME": "unchanged value", "CHANGED": "new value", "SESSION_ID": "generated-id",
                 "API_KEY": "not-a-secret", "EMPTY": "", "SPACES": "  ", "CONFIG": "x" * 1024,
                 "MULTILINE": "one\n`two`|<three>", "invalid-name/path": "omitted name"}
        script = 'import { compareEnvironment } from "./tests/harnesses/discover.mjs"; console.log(JSON.stringify(compareEnvironment(' + json.dumps(before) + ',' + json.dumps(after) + ')));'
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=run.ROOT,
                                capture_output=True, text=True, check=True)
        observed = json.loads(result.stdout)
        expected = {name: {"change": "unchanged" if name == "SAME" else "changed" if name == "CHANGED" else "added",
                           "nonblank": bool(value.strip()), "value": value}
                    for name, value in after.items() if name != "invalid-name/path"}
        expected["REMOVED"] = {"change": "removed", "nonblank": False, "value": None}
        self.assertEqual(observed, expected)
        record = {"schema": 3, "nonce": "fresh", "environment": observed, "ancestry": ["node"]}
        self.assertEqual(run.validate_discovery(record, "fresh"), record)

    def test_value_schema_rejects_wrong_types_or_inconsistent_presence(self):
        record = {"schema": 3, "nonce": "fresh", "environment": {}, "ancestry": ["node"]}
        for info in [{"change": "added", "nonblank": True, "value": None},
                     {"change": "added", "nonblank": True, "value": 1},
                     {"change": "added", "nonblank": False, "value": "text"},
                     {"change": "removed", "nonblank": False, "value": ""},
                     {"change": "removed", "nonblank": True, "value": None}]:
            with self.subTest(info=info), self.assertRaises(ValueError):
                run.validate_discovery({**record, "environment": {"NEW": info}}, "fresh")

    def test_unknown_fields_values_paths_and_stale_discovery_are_rejected(self):
        record = {"schema": 1, "nonce": "fresh", "environment": {
            "API_KEY": {"change": "added", "nonblank": True}}, "ancestry": ["agent-probe", "goose"]}
        self.assertEqual(run.validate_discovery(record, "fresh"), record)
        for changed in [{"nonce": "stale"}, {"argv": "secret"}, {"ancestry": ["/private/goose"]},
                        {"ancestry": [{}]}, {"ancestry": []},
                        {"environment": {"API_KEY": {"change": "added", "nonblank": "secret"}}},
                        {"environment": {"API_KEY": {"change": "added", "nonblank": True, "value": "secret"}}},
                        {"environment": {"bad-name": {"change": "added", "nonblank": True}}}]:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                run.validate_discovery({**record, **changed}, "fresh")


class GatewayTests(unittest.TestCase):
    def setUp(self):
        gateway.Handler.evidence = {"calls": [], "results": [], "final_responses": 0}

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

    def test_request_budget(self):
        handler = self.handler()
        gateway.Handler.count = 6
        statuses = []
        handler.send_response = statuses.append
        handler.do_POST()
        self.assertEqual(statuses, [429])

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

    def test_junie_finishes_with_advertised_submit_without_another_shell_call(self):
        handler = self.handler({"messages": [{"role": "tool", "tool_call_id": "callprobe", "content": "probe output"}],
            "tools": [{"function": {"name": "submit", "parameters": {"properties": {"solution_summary": {"type": "string"}}}}}]})
        handler.do_POST()
        response = json.loads(handler.wfile.getvalue())["choices"][0]
        self.assertEqual(response["message"]["tool_calls"][0]["function"]["name"], "submit")
        self.assertEqual(gateway.Handler.evidence["calls"], [])
        self.assertEqual(gateway.Handler.evidence["final_responses"], 1)


class ProviderEvidenceTests(unittest.TestCase):
    def test_only_correlated_successful_shell_output_passes(self):
        evidence = {"calls": [{"id": "callprobe", "name": "bash", "command": "probe"}],
                    "results": [{"id": "callprobe", "content": '{"agent":"crush"}', "is_error": False}],
                    "final_responses": 1}
        def verify(value):
            return all(run.verify_provider(value, "probe", {"agent": "crush"}, "bash").values())
        self.assertTrue(verify(evidence))
        for call in [{"command": "echo fake"}, {"name": "write_file"}]:
            self.assertFalse(verify({**evidence, "calls": [{**evidence["calls"][0], **call}]}))
        for result in [{"id": "unrelated"}, {"is_error": True}, {"content": "Done"}, {"content": '{"agent":"goose"}'}]:
            self.assertFalse(verify({**evidence, "results": [{**evidence["results"][0], **result}]}))
        for field in ["calls", "results"]:
            self.assertFalse(verify({**evidence, field: evidence[field] * 2}))
            self.assertFalse(verify({**evidence, field: []}))
        self.assertFalse(verify({**evidence, "final_responses": 0}))

    def test_nested_gemini_tool_output_is_compared_to_full_probe(self):
        probe = {"agent": "gemini-cli", "nonce": "fresh"}
        content = json.dumps({"output": "Output: " + json.dumps(probe) + "\nProcess exited"})
        self.assertTrue(run.output_matches(content, probe))
        self.assertFalse(run.output_matches(content, {**probe, "nonce": "stale"}))

    def test_collection_does_not_require_a_detector_rule(self):
        # These are legitimate observations from the unchanged library: no
        # detection, an unrecognised generic identity, or a fork's parent identity.
        for agent in [None, "unknown", "opencode", "pi"]:
            report = {"probe": {"agent": agent}, "checks": {
                "real_shell_tool_executed": True, "harness_identified": False,
                "configured_environment_not_detected": False}}
            self.assertEqual(run.classify_result(report), "pass")
            report["checks"]["real_shell_tool_executed"] = False
            self.assertEqual(run.classify_result(report), "fail")


class GatewayHTTPTests(unittest.TestCase):
    """Exercise actual HTTP/stream serialization, not just handler methods."""
    def setUp(self):
        gateway.Handler.count = 0
        gateway.Handler.evidence = {"calls": [], "results": [], "final_responses": 0}
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), gateway.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def post(self, path, body):
        request = urllib.request.Request(self.base + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=2) as response:
            return response.read().decode()

    def test_all_four_protocols_produce_and_observe_a_real_tool_roundtrip(self):
        command = "/usr/local/bin/agent-probe /artifacts/agent.json " + "b" * 32 + " --discover"
        probe = {"agent": "test", "nonce": "b" * 32}
        output = json.dumps(probe)
        parameters = {"type": "object", "properties": {"command": {"type": "string"}}}
        tool = {"name": "bash", "parameters": parameters}
        fixtures = [
            ("/v1/chat/completions", {"stream": True, "messages": [{"role": "user", "content": command}],
                "tools": [{"type": "function", "function": tool}]},
                {"messages": [{"role": "tool", "tool_call_id": "callprobe", "content": output}]}),
            ("/v1/responses", {"stream": True, "input": [{"role": "user", "content": command}],
                "tools": [{"type": "function", **tool}]},
                {"input": [{"type": "function_call_output", "call_id": "callprobe", "output": output}]}),
            ("/v1/messages?beta=true", {"stream": True, "messages": [{"role": "user", "content": command}],
                "tools": [{"name": "bash", "input_schema": parameters}]},
                {"messages": [{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "callprobe", "content": output}]}]}),
            ("/v1beta/models/test:streamGenerateContent?alt=sse", {"contents": [{"role": "user", "parts": [{"text": command}]}],
                "tools": [{"functionDeclarations": [tool]}]},
                {"contents": [{"role": "user", "parts": [{"functionResponse": {"name": "bash", "id": "callprobe", "response": {"output": output}}}]}]}),
        ]
        for path, initial, followup in fixtures:
            with self.subTest(protocol=path):
                gateway.Handler.count = 0
                gateway.Handler.evidence = {"calls": [], "results": [], "final_responses": 0}
                response = self.post(path, initial)
                self.assertIn("callprobe", response)
                self.assertIn(command, response)
                self.post(path, {**initial, **followup})
                with urllib.request.urlopen(self.base + "/evidence", timeout=2) as response:
                    evidence = json.load(response)
                self.assertTrue(all(run.verify_provider(evidence, command, probe, "bash").values()))

    def test_cline_receives_one_command_in_its_advertised_array_schema(self):
        command = "/usr/local/bin/agent-probe /artifacts/agent.json " + "c" * 32
        body = {"messages": [{"role": "user", "content": command}], "tools": [{"type": "function", "function": {
            "name": "run_commands", "parameters": {"properties": {"commands": {"type": "array", "items": {"type": "string"}}}}}}]}
        response = json.loads(self.post("/v1/chat/completions", body))
        call = response["choices"][0]["message"]["tool_calls"][0]
        self.assertEqual(json.loads(call["function"]["arguments"]), {"commands": [command]})


if __name__ == "__main__":
    unittest.main()
