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
    discovery = {"schema": 2, "nonce": nonce, "ancestry": ["pi"], "environment": {
        "PI_CODING_AGENT": {"change": "added", "nonblank": True, "value": "1"},
        "PATH": {"change": "unchanged", "nonblank": True, "value": "<redacted>"}}}
    return {"harness": name, "harness_version": run.HARNESS[name]["version"], "stage": "complete",
            "status": "pass", "mode": "mock", "platform": "linux/amd64", "timestamp": "2026-09-23T15:00:00+00:00",
            "checks": {"real_shell_tool_executed": True}, "probe": probe, "control": control,
            "configured_control": control, "discovery": {"agent": discovery, "configured": discovery},
            **{key: "b" * 64 for key in inventory.PROVENANCE}}


def document():
    return {"pi": inventory.observation(report())}


def write_pair(artifacts, candidate=None, attempt=1):
    folder = artifacts / f"watch-pi-123-{attempt}" / "uuid"
    folder.mkdir(parents=True)
    (folder / "comparison.json").write_text("{}")
    (folder / "baseline.json").write_text(json.dumps(report()))
    candidate = candidate or report(nonce="b" * 32)
    (folder / "candidate.json").write_text(json.dumps(candidate))
    (folder / "resolved.json").write_text(json.dumps({"version": candidate.get("harness_version", "0.88.0")}))
    return folder


class InventoryTests(unittest.TestCase):
    def test_flat_inventory_keeps_values_blank_and_inherited_but_omits_removed(self):
        r = report()
        r["discovery"]["agent"]["environment"].update({
            "AI_AGENT": {"change": "added", "nonblank": True, "value": "pi"},
            "EMPTY": {"change": "unchanged", "nonblank": False, "value": ""},
            "REMOVED": {"change": "removed", "nonblank": False, "value": None},
        })
        doc = {"pi": inventory.observation(r)}
        self.assertEqual(doc, {"pi": {"PI_CODING_AGENT": "1", "PATH": "<redacted>", "AI_AGENT": "pi", "EMPTY": ""}})
        sheet = inventory.render(doc)
        self.assertIn("| `AI_AGENT` | `pi` |", sheet)
        self.assertIn('| `EMPTY` | `""` |', sheet)
        self.assertEqual(sheet, inventory.render(json.loads(json.dumps(doc, sort_keys=True))))

    def test_names_and_values_are_diffed_without_interpreting_detector_rules(self):
        before = document()
        after = copy.deepcopy(before)
        del after["pi"]["PI_CODING_AGENT"]
        after["pi"]["AGENT"] = "pi"
        after["pi"]["PATH"] = ""
        self.assertEqual(inventory.difference(before, after), {"pi": {
            "added": {"AGENT": "pi"}, "removed": {"PI_CODING_AGENT": "1"},
            "changed": {"PATH": {"before": "<redacted>", "after": ""}}}})

    def test_version_date_and_detection_are_not_inventory_fields(self):
        r = report()
        before = inventory.observation(r)
        r.update(harness_version="0.88.0", timestamp="2026-09-30T15:00:00+00:00", status="fail")
        r["probe"]["agent"] = None
        self.assertEqual(before, inventory.observation(r))

    def test_unknown_names_are_retained_but_unapproved_values_are_rejected(self):
        r = report()
        env = r["discovery"]["agent"]["environment"]
        env["new_agent_context"] = {"change": "added", "nonblank": True, "value": "<redacted>"}
        self.assertIn("new_agent_context", inventory.observation(r))
        for name, value in [("new_agent_context", "sentinel-secret"), ("TOKEN", "true"), ("SESSION_ID", "1")]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                inventory.validate_document({"pi": {name: value}})
        env["new_agent_context"]["value"] = "sentinel-secret"
        with self.assertRaises(ValueError):
            inventory.observation(r)

    def test_historical_reports_cannot_invent_values(self):
        r = report()
        r["discovery"]["agent"]["schema"] = 1
        for info in r["discovery"]["agent"]["environment"].values():
            del info["value"]
        with self.assertRaises(ValueError):
            inventory.observation(r)

    def test_failed_or_missing_probe_preserves_old_inventory(self):
        old = document()
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory)
            current, errors, runs = inventory.collect(old, artifacts, ["pi"], RUN_URL)
            self.assertEqual(current, old)
            self.assertEqual(errors["pi"]["stage"], "missing")
            self.assertFalse(runs)
            write_pair(artifacts, {"status": "error", "stage": "agent"})
            current, errors, runs = inventory.collect(old, artifacts, ["pi"], RUN_URL)
            self.assertEqual(current, old)
            self.assertEqual(errors["pi"]["reason"], "unverified_execution")

    def test_detection_change_stays_in_run_report_and_source_mismatch_is_rejected(self):
        old = document()
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory)
            candidate = report(nonce="b" * 32)
            candidate["status"] = "fail"
            candidate["probe"]["agent"] = None
            folder = write_pair(artifacts, candidate)
            current, errors, runs = inventory.collect(old, artifacts, ["pi"], RUN_URL)
            self.assertFalse(errors)
            self.assertEqual(current, old)
            self.assertEqual(runs["pi"]["outcome"], "detection_regression")
            candidate["probe_source_sha256"] = "f" * 64
            (folder / "candidate.json").write_text(json.dumps(candidate))
            current, errors, runs = inventory.collect(old, artifacts, ["pi"], RUN_URL)
            self.assertEqual(current, old)
            self.assertTrue(errors)

    def test_rerun_uses_latest_attempt_without_version_churn_in_inventory(self):
        old = document()
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory)
            write_pair(artifacts)
            candidate = report(nonce="b" * 32)
            candidate["harness_version"] = "0.88.0"
            write_pair(artifacts, candidate, attempt=2)
            current, errors, runs = inventory.collect(old, artifacts, ["pi"], RUN_URL)
            self.assertFalse(errors)
            self.assertEqual(current, old)
            self.assertEqual(runs["pi"]["candidate_version"], "0.88.0")


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
        self.runs = {"pi": {"pinned_version": "0.87.1", "candidate_version": "0.87.1", "outcome": "unchanged"}}

    def publish(self, errors=None):
        return publisher.publish(self.api, self.old, self.new, errors or {}, {k: v for k, v in self.runs.items() if k not in (errors or {})}, default_branch="main", tested_sha=SHA, run_url=RUN_URL)

    def test_version_only_does_not_write_and_variable_change_opens_scoped_pr(self):
        self.publish()
        self.assertFalse([c for c in self.api.calls if c[1] != "GET"])
        self.runs["pi"]["candidate_version"] = "0.88.0"
        self.publish()
        self.assertFalse([c for c in self.api.calls if c[1] != "GET"])
        self.new["pi"]["AGENT"] = "pi"
        self.publish()
        writes = [c for c in self.api.calls if c[1] != "GET"]
        self.assertIn("pulls", [c[0] for c in writes])
        self.assertIn("issues", [c[0] for c in writes])
        tree = next(c[2] for c in writes if c[0] == "git/trees")
        self.assertEqual({f["path"] for f in tree["tree"]}, publisher.PATHS)
        self.assertFalse(any("heads/main" in c[0] for c in writes))

    def test_meaningful_change_opens_deduplicated_issue_and_never_reopens_acknowledged_issue(self):
        self.new["pi"]["NEW_FLAG"] = "1"
        self.publish()
        issue = next(c[2] for c in self.api.calls if c[0] == "issues" and c[1] == "POST")
        self.api.issues = [{"number": 8, "state": "closed", "user": {"login": "github-actions[bot]"}, "body": issue["body"]}]
        self.api.calls.clear()
        self.publish()
        self.assertFalse([c for c in self.api.calls if c[0].startswith("issues") and c[1] != "GET"])

    def test_detection_alert_without_inventory_change_opens_issue_only(self):
        self.runs["pi"]["outcome"] = "detection_regression"
        self.publish()
        writes = [c for c in self.api.calls if c[1] != "GET"]
        self.assertEqual([c[0] for c in writes], ["issues"])
        self.assertIn("detection_regression", writes[0][2]["body"])

    def test_failure_reports_issue_and_keeps_old_inventory_without_pr(self):
        self.publish({"pi": {"stage": "agent", "reason": "unverified_execution"}})
        writes = [c[0] for c in self.api.calls if c[1] != "GET"]
        self.assertEqual(writes, ["issues"])

    def test_failure_in_a_different_version_is_not_silenced_by_old_closed_issue(self):
        self.publish({"pi": {"stage": "agent", "reason": "unverified_execution", "version": "0.88.0"}})
        old = next(c[2] for c in self.api.calls if c[0] == "issues" and c[1] == "POST")
        self.api.issues = [{"number": 8, "state": "closed", "user": {"login": "github-actions[bot]"}, "body": old["body"]}]
        self.api.calls.clear()
        self.publish({"pi": {"stage": "agent", "reason": "unverified_execution", "version": "0.89.0"}})
        self.assertTrue([c for c in self.api.calls if c[0] == "issues" and c[1] == "POST"])

    def test_stale_run_or_unrelated_branch_changes_cannot_be_overwritten(self):
        self.api.head = "f" * 40
        with self.assertRaises(ValueError):
            self.publish()
        self.assertFalse([c for c in self.api.calls if c[1] != "GET"])
        self.api.head = SHA
        self.new["pi"]["NEW_FLAG"] = "1"
        self.api.refs = [{"ref": "refs/heads/" + publisher.BRANCH, "object": {"sha": "a" * 40}}]
        self.api.files = [{"filename": "src/lib.rs"}]
        with self.assertRaises(ValueError):
            self.publish()
        self.assertFalse([c for c in self.api.calls if c[1] != "GET"])

    def test_existing_proposal_is_updated_without_force_push_or_default_branch_write(self):
        self.api.prs = [{"number": 7, "body": publisher.MARKER, "user": {"login": "github-actions[bot]"}}]
        self.api.refs = [{"ref": "refs/heads/" + publisher.BRANCH, "object": {"sha": "a" * 40}}]
        self.api.files = [{"filename": str(inventory.DATA)}]
        self.new["pi"]["NEW_FLAG"] = "1"
        self.publish()
        writes = [c for c in self.api.calls if c[1] != "GET"]
        commit = next(c[2] for c in writes if c[0] == "git/commits")
        self.assertEqual(commit["parents"], ["a" * 40, SHA])
        ref = next(c for c in writes if c[0].startswith("git/refs/"))
        self.assertFalse(ref[2]["force"])
        self.assertIn("codex%2Fharness-inventory", ref[0])
        self.assertIn("pulls/7", [c[0] for c in writes])
        self.assertNotIn("pulls", [c[0] for c in writes])

    def test_artifact_values_or_failed_snapshot_replacement_cannot_be_published(self):
        self.new["pi"]["TOKEN"] = "sentinel-secret"
        with self.assertRaises(ValueError):
            self.publish()
        self.new = copy.deepcopy(self.old)
        self.new["pi"]["NEW_FLAG"] = "1"
        with self.assertRaises(ValueError):
            self.publish({"pi": {"stage": "agent", "reason": "unverified_execution"}})
        self.assertEqual(self.api.calls, [])


if __name__ == "__main__":
    unittest.main()
