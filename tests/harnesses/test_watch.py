import base64
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import releases
import run
import watch


class ReleaseTests(unittest.TestCase):
    def test_npm_latest_is_resolved_once_without_changing_contract_or_pin(self):
        pinned = copy.deepcopy(run.HARNESS["cline"])
        with patch.object(releases, "json_url", return_value={"version": "3.1.0", "dist": {"integrity": "sha512-YWJjZA=="}}) as get:
            candidate = releases.resolve("cline", pinned)
        self.assertTrue(get.call_args.args[0].endswith("/cline/latest"))
        self.assertEqual(candidate["version"], "3.1.0")
        self.assertEqual(candidate["known_gap"], pinned["known_gap"])
        self.assertEqual(candidate["markers"], pinned["markers"])
        self.assertEqual(pinned, run.HARNESS["cline"])
        for version in ["latest", "^1.0.0", "1.0.0; echo bad"]:
            with self.assertRaises(ValueError):
                releases.exact_version(version)

    def test_exact_selection_cannot_silently_resolve_a_different_version(self):
        with patch.object(releases, "json_url", return_value={"version": "3.1.0"}):
            with self.assertRaises(ValueError):
                releases.resolve("cline", run.HARNESS["cline"], "3.0.64")

    def test_release_assets_keep_official_digest_and_exact_version(self):
        assets = [{"name": f"goose-{arch}-unknown-linux-musl.tar.gz",
                   "browser_download_url": f"https://github.com/aaif-goose/goose/releases/download/v1.53.0/goose-{arch}.tar.gz",
                   "digest": "sha256:" + "a" * 64} for arch in ("aarch64", "x86_64")]
        with patch.object(releases, "json_url", return_value={"tag_name": "v1.53.0", "assets": assets}):
            spec = releases.resolve("goose", run.HARNESS["goose"])
        self.assertEqual(spec["version"], "1.53.0")
        self.assertEqual(spec["assets"]["x64"]["sha256"], "a" * 64)
        self.assertTrue(spec["known_gap"])
        with patch.object(releases, "read_url", return_value=b"public archive"):
            asset = releases.release_asset({"assets": [{**assets[0], "digest": None}]}, assets[0]["name"])
        self.assertEqual(asset["sha256"], hashlib.sha256(b"public archive").hexdigest())

    def test_hermes_pins_resolved_commit_not_moving_release_tag(self):
        sha = "b" * 40
        with patch.object(releases, "json_url", side_effect=[{"tag_name": "v2026.10.1"}, {"sha": sha}]), \
             patch.object(releases, "read_url", side_effect=[b'[project]\nversion = "0.22.0"\n', b"archive"]):
            spec = releases.resolve("hermes-agent", run.HARNESS["hermes-agent"])
        self.assertEqual(spec["version"], "0.22.0")
        self.assertTrue(spec["source"]["url"].endswith(sha))
        self.assertEqual(spec["source"]["sha256"], hashlib.sha256(b"archive").hexdigest())

    def test_junie_resolves_npm_and_reported_binary_versions(self):
        mapping = json.dumps({"version": "3419.7", "marketing": "26.9.22"}).encode()
        with patch.object(releases, "json_url", side_effect=[
                {"version": "3419.7.0", "dist": {"integrity": "sha512-YWJjZA=="}},
                {"content": base64.b64encode(mapping).decode()}]):
            spec = releases.resolve("junie", run.HARNESS["junie"])
        self.assertEqual(spec["reported_version"], "26.9.22 (3419.7)")

    def test_multiple_reviewed_versions_include_their_own_expectations(self):
        spec = {"version": "1.2.0", "known_gap": "Absent", "compatibility_versions": [
            {"version": "1.1.0", "known_gap": None}]}
        self.assertEqual(releases.matrix({"test": spec}), {"include": [
            {"harness": "test", "version": "1.2.0", "expected_gap": True},
            {"harness": "test", "version": "1.1.0", "expected_gap": False}]})
        with self.assertRaises(ValueError):
            releases.pinned_spec({**spec, "assets": {}}, "1.1.0")
        with self.assertRaises(ValueError):
            releases.matrix({"test": {**spec, "compatibility_versions": [{"version": "1.2.0"}]}})


class WatchTests(unittest.TestCase):
    def report(self, agent=None):
        return {"harness": "goose", "platform": "linux/amd64", "stage": "complete",
                "status": "pass" if agent else "known-gap",
                "checks": {"real_shell_tool_executed": True},
                "probe": {"agent": agent, "signal": "GOOSE_TERMINAL" if agent else None,
                          "nonce": "fresh", "markers": {"GOOSE_TERMINAL": bool(agent)}},
                "discovery": {"agent": {"schema": 1, "nonce": "fresh", "ancestry": ["goose"], "environment": {}}}}

    def test_expected_absence_is_quiet_but_new_identity_alerts(self):
        self.assertEqual(watch.assess(self.report(), self.report())["outcome"], "unchanged")
        new = self.report("goose")
        new["status"] = "fail"  # The old known-gap contract is now violated.
        self.assertEqual(watch.assess(self.report(), new)["outcome"], "new_detection")

    def test_removed_identity_is_regression_only_after_real_execution(self):
        before, after = self.report("goose"), self.report()
        self.assertEqual(watch.assess(before, after)["outcome"], "detection_regression")
        after["checks"]["real_shell_tool_executed"] = False
        self.assertEqual(watch.assess(before, after)["outcome"], "execution_failed")
        before["status"] = "error"
        self.assertEqual(watch.assess(before, after)["outcome"], "baseline_failed")

    def test_unknown_new_variable_is_candidate_without_library_rule(self):
        before, after = self.report(), self.report()
        after["discovery"]["agent"]["environment"]["NEW_PRODUCT_AGENT"] = {"change": "added", "nonblank": True}
        result = watch.assess(before, after)
        self.assertEqual(result["outcome"], "new_candidates")
        self.assertEqual(result["candidates"], ["NEW_PRODUCT_AGENT"])
        after["discovery"]["non_agent"] = {"environment": {"NEW_PRODUCT_AGENT": {"nonblank": True}}}
        self.assertEqual(watch.assess(before, after)["outcome"], "observations_changed")

    def test_existing_marker_or_session_contract_changes_are_not_silenced(self):
        before, after = self.report("goose"), self.report("goose")
        after["probe"]["markers"]["GOOSE_TERMINAL"] = False
        after["status"] = "fail"
        self.assertEqual(watch.assess(before, after)["outcome"], "contract_changed")
        after["platform"] = "linux/arm64"
        with self.assertRaises(ValueError):
            watch.assess(before, after)

    def test_changed_value_of_existing_marker_is_not_a_new_candidate(self):
        before, after = self.report("goose"), self.report("goose")
        for report, value in [(before, "goose_1-52-0_agent"), (after, "goose_1-53-0_agent")]:
            report["discovery"]["agent"]["schema"] = 3
            report["discovery"]["agent"]["environment"]["AI_AGENT"] = {
                "change": "added", "nonblank": True, "value": value}
        result = watch.assess(before, after)
        self.assertEqual(result["outcome"], "observations_changed")
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["changes"]["environment.AI_AGENT"]["after"]["value"], "goose_1-53-0_agent")

    def test_unknown_values_and_changing_session_ids_are_compared_exactly(self):
        before, after = self.report(), self.report()
        for report, session in [(before, "generated-session-one"), (after, "generated-session-two")]:
            report["discovery"]["agent"]["schema"] = 3
            report["discovery"]["agent"]["environment"]["SESSION_ID"] = {
                "change": "added", "nonblank": True, "value": session}
        after["discovery"]["agent"]["environment"]["NEW_AGENT"] = {
            "change": "added", "nonblank": True, "value": "unfamiliar-value"}
        result = watch.assess(before, after)
        self.assertEqual(result["changes"]["environment.NEW_AGENT"]["after"]["value"], "unfamiliar-value")
        self.assertEqual(result["changes"]["environment.SESSION_ID"]["after"]["value"], "generated-session-two")
        self.assertEqual(result["candidates"], ["NEW_AGENT"])

    def test_watcher_records_resolution_and_both_fresh_runs(self):
        spec = {**run.HARNESS["goose"], "version": "1.53.0"}
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(run, "ROOT", Path(directory)), \
             patch("sys.argv", ["watch.py", "--harness", "goose"]), \
             patch.dict(watch.os.environ, {"GITHUB_STEP_SUMMARY": str(Path(directory) / "job.md")}), \
             patch.object(releases, "resolve", return_value=spec), \
             patch.object(watch, "execute", side_effect=[self.report(), self.report()]) as execute, \
             patch("builtins.print"):
            self.assertEqual(watch.main(), 0)
            self.assertEqual([call.args[1]["version"] for call in execute.call_args_list], [run.HARNESS["goose"]["version"], "1.53.0"])
            artifacts = next((Path(directory) / "target/harness-watch/goose").iterdir())
            self.assertEqual(json.loads((artifacts / "resolved.json").read_text())["version"], "1.53.0")
            self.assertEqual(json.loads((artifacts / "comparison.json").read_text())["outcome"], "unchanged")
            self.assertTrue((artifacts / "baseline.json").exists())
            self.assertTrue((artifacts / "candidate.json").exists())
            self.assertIn("unchanged", (Path(directory) / "job.md").read_text())

    def test_resolution_failure_still_writes_safe_actionable_artifacts(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(run, "ROOT", Path(directory)), \
             patch("sys.argv", ["watch.py", "--harness", "goose"]), \
             patch.dict(watch.os.environ, {"GITHUB_STEP_SUMMARY": str(Path(directory) / "job.md")}), \
             patch.object(releases, "resolve", side_effect=OSError("sentinel-secret")), \
             patch.object(watch, "execute") as execute, patch("builtins.print"):
            self.assertEqual(watch.main(), 1)
            execute.assert_not_called()
            artifacts = next((Path(directory) / "target/harness-watch/goose").iterdir())
            result = json.loads((artifacts / "comparison.json").read_text())
            self.assertEqual(result["outcome"], "resolution_or_evidence_error")
            self.assertEqual(result["error_type"], "OSError")
            self.assertNotIn("sentinel-secret", (artifacts / "summary.md").read_text())


if __name__ == "__main__":
    unittest.main()
