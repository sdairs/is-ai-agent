import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import inventory
import publish_inventory as publisher
import run

RUN_URL = "https://github.com/example/repo/actions/runs/123"
SHA = "c" * 40


def report(name="pi", nonce="a" * 32):
    probe = {"schema": 4, "nonce": nonce, "library_version": run.library_version(),
             "agent": name, "signal": "PI_CODING_AGENT", "session_present": False,
             "markers": {key: key == "PI_CODING_AGENT" for key in run.MARKERS},
             "exact_markers": {key: False for key in run.EXACT_MARKERS},
             "session_matches": {key: False for key in run.SESSIONS},
             "generic_markers": {"AGENT": None, "AI_AGENT": None}}
    control = {**probe, "agent": None, "signal": None, "markers": {key: False for key in run.MARKERS}}
    discovery = {"schema": 1, "nonce": nonce, "ancestry": ["pi"], "environment": {
        "PI_CODING_AGENT": {"change": "added", "nonblank": True},
        "PATH": {"change": "unchanged", "nonblank": True}}}
    return {"harness": name, "harness_version": run.HARNESS[name]["version"], "stage": "complete",
            "status": "pass", "mode": "mock", "platform": "linux/amd64", "timestamp": "2026-09-23T15:00:00+00:00",
            "checks": {"real_shell_tool_executed": True}, "probe": probe, "control": control,
            "configured_control": control, "discovery": {"agent": discovery, "configured": discovery},
            **{key: "b" * 64 for key in inventory.PROVENANCE}}


def document():
    return {"schema": 1, "harnesses": {"pi": inventory.observation(report(), RUN_URL)}}


class InventoryTests(unittest.TestCase):
    def test_unrelated_generic_addition_is_visible_while_detection_stays_working(self):
        before = document()["harnesses"]["pi"]
        after = copy.deepcopy(before)
        after["environment"]["AGENT"] = {"change": "added", "nonblank": True}
        after["detection"]["generic_markers"]["AGENT"] = "pi"
        self.assertEqual(inventory.delta(before, after)["kind"], "signals_changed_detection_preserved")
        self.assertIn("detection.generic_markers.AGENT", inventory.delta(before, after)["changes"])

    def test_legacy_marker_removed_with_generic_replacement_is_not_called_regression(self):
        before = document()["harnesses"]["pi"]
        after = copy.deepcopy(before)
        del after["environment"]["PI_CODING_AGENT"]
        after["detection"]["markers"]["PI_CODING_AGENT"] = False
        after["detection"]["signal"] = "AGENT"
        after["detection"]["generic_markers"]["AGENT"] = "pi"
        self.assertEqual(inventory.delta(before, after)["kind"], "signals_changed_detection_preserved")
        after["detection"]["agent"] = None
        self.assertEqual(inventory.delta(before, after)["kind"], "detection_changed")
        after["evidence"]["library_source_sha256"] = "d" * 64
        self.assertEqual(inventory.delta(before, after)["kind"], "measurement_changed_review_required")

    def test_timestamp_only_is_quiet_and_version_only_is_not_a_signal_alert(self):
        before = document()["harnesses"]["pi"]
        after = copy.deepcopy(before)
        after["evidence"]["run_url"] += "4"
        after["evidence"]["observed_at"] = "2026-09-30T15:00:00+00:00"
        self.assertIsNone(inventory.delta(before, after))
        after["version"] = "0.88.0"
        self.assertEqual(inventory.delta(before, after)["kind"], "version_or_measurement_only")

    def test_unknown_new_names_are_retained_with_no_raw_values_or_inferred_rules(self):
        r = report()
        r["discovery"]["agent"]["environment"]["new_agent_context"] = {"change": "added", "nonblank": True}
        entry = inventory.observation(r, RUN_URL)
        doc = {"schema": 1, "harnesses": {"pi": entry}}
        self.assertIn("new_agent_context", inventory.render(doc))
        self.assertIn("untested", inventory.render(doc))
        r["discovery"]["agent"]["environment"]["new_agent_context"]["value"] = "sentinel-secret"
        with self.assertRaises(ValueError):
            inventory.observation(r, RUN_URL)

    def test_failed_or_missing_probe_preserves_old_inventory(self):
        old = document()
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory)
            current, errors = inventory.collect(old, artifacts, ["pi"], RUN_URL)
            self.assertEqual(current, old)
            self.assertEqual(errors["pi"]["stage"], "missing")
            folder = artifacts / "watch-pi-123-1" / "uuid"
            folder.mkdir(parents=True)
            (folder / "comparison.json").write_text("{}")
            (folder / "baseline.json").write_text(json.dumps(report()))
            (folder / "candidate.json").write_text(json.dumps({"status": "error", "stage": "agent"}))
            current, errors = inventory.collect(old, artifacts, ["pi"], RUN_URL)
            self.assertEqual(current, old)
            self.assertEqual(errors["pi"]["reason"], "unverified_execution")

    def test_verified_contract_change_is_recorded_and_source_mismatch_is_rejected(self):
        old = document()
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory)
            folder = artifacts / "watch-pi-123-1" / "uuid"
            folder.mkdir(parents=True)
            (folder / "comparison.json").write_text("{}")
            (folder / "baseline.json").write_text(json.dumps(report()))
            candidate = report(nonce="b" * 32)
            candidate["status"] = "fail"
            candidate["probe"]["agent"] = None
            (folder / "candidate.json").write_text(json.dumps(candidate))
            (folder / "resolved.json").write_text(json.dumps({"version": candidate["harness_version"]}))
            current, errors = inventory.collect(old, artifacts, ["pi"], RUN_URL)
            self.assertFalse(errors)
            self.assertIsNone(current["harnesses"]["pi"]["detection"]["agent"])
            candidate["probe_source_sha256"] = "f" * 64
            (folder / "candidate.json").write_text(json.dumps(candidate))
            current, errors = inventory.collect(old, artifacts, ["pi"], RUN_URL)
            self.assertEqual(current, old)
            self.assertTrue(errors)


class FakeGitHub:
    prefix = "repos/example/repo/"

    def __init__(self):
        self.calls, self.issues, self.prs, self.refs = [], [], [], []
        self.head = SHA
        self.files = []

    def call(self, path, method="GET", payload=None, paginate=False):
        self.calls.append((path, method, payload))
        if path == "git/ref/heads/main":
            return {"object": {"sha": self.head}}
        if path.startswith("pulls?"):
            return self.prs
        if path.startswith("git/matching-refs/"):
            return self.refs
        if path.startswith("compare/"):
            return {"files": self.files}
        if path.startswith("git/commits/"):
            return {"tree": {"sha": "d" * 40}}
        if path in {"git/trees", "git/commits"}:
            return {"sha": "e" * 40}
        if path.startswith("issues?"):
            return self.issues
        if path.startswith("pulls"):
            return {"html_url": "https://github.com/example/repo/pull/7"}
        return {}


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.scope = patch.dict(run.HARNESS, {"pi": run.HARNESS["pi"]}, clear=True)
        self.scope.start()
        self.addCleanup(self.scope.stop)
        self.api = FakeGitHub()
        self.old = document()
        self.new = copy.deepcopy(self.old)

    def publish(self, errors=None):
        return publisher.publish(self.api, self.old, self.new, errors or {}, default_branch="main", tested_sha=SHA, run_url=RUN_URL)

    def test_no_change_does_not_write_and_version_only_opens_pr_without_issue(self):
        self.publish()
        self.assertFalse([c for c in self.api.calls if c[1] != "GET"])
        self.new["harnesses"]["pi"]["version"] = "0.88.0"
        self.publish()
        writes = [c for c in self.api.calls if c[1] != "GET"]
        self.assertIn("pulls", [c[0] for c in writes])
        self.assertNotIn("issues", [c[0] for c in writes])
        tree = next(c[2] for c in writes if c[0] == "git/trees")
        self.assertEqual({f["path"] for f in tree["tree"]}, publisher.PATHS)
        self.assertFalse(any("heads/main" in c[0] for c in writes))

    def test_meaningful_change_opens_deduplicated_issue_and_never_reopens_acknowledged_issue(self):
        self.new["harnesses"]["pi"]["environment"]["NEW_FLAG"] = {"change": "added", "nonblank": True}
        self.publish()
        issue = next(c[2] for c in self.api.calls if c[0] == "issues" and c[1] == "POST")
        self.api.issues = [{"number": 8, "state": "closed", "user": {"login": "github-actions[bot]"}, "body": issue["body"]}]
        self.api.calls.clear()
        self.publish()
        self.assertFalse([c for c in self.api.calls if c[0].startswith("issues") and c[1] != "GET"])

    def test_failure_reports_issue_and_keeps_old_inventory_without_pr(self):
        self.publish({"pi": {"stage": "agent", "reason": "unverified_execution"}})
        writes = [c[0] for c in self.api.calls if c[1] != "GET"]
        self.assertEqual(writes, ["issues"])

    def test_stale_run_or_unrelated_branch_changes_cannot_be_overwritten(self):
        self.api.head = "f" * 40
        with self.assertRaises(ValueError):
            self.publish()
        self.assertFalse([c for c in self.api.calls if c[1] != "GET"])
        self.api.head = SHA
        self.new["harnesses"]["pi"]["version"] = "0.88.0"
        self.api.refs = [{"ref": "refs/heads/" + publisher.BRANCH, "object": {"sha": "a" * 40}}]
        self.api.files = [{"filename": "src/lib.rs"}]
        with self.assertRaises(ValueError):
            self.publish()
        self.assertFalse([c for c in self.api.calls if c[1] != "GET"])

    def test_artifact_values_or_failed_snapshot_replacement_cannot_be_published(self):
        self.new["harnesses"]["pi"]["environment"]["TOKEN"] = {"change": "added", "nonblank": True, "value": "sentinel-secret"}
        with self.assertRaises(ValueError):
            self.publish()
        self.new = copy.deepcopy(self.old)
        self.new["harnesses"]["pi"]["version"] = "0.88.0"
        with self.assertRaises(ValueError):
            self.publish({"pi": {"stage": "agent", "reason": "unverified_execution"}})
        self.assertEqual(self.api.calls, [])


if __name__ == "__main__":
    unittest.main()
