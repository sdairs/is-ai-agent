#!/usr/bin/env python3
"""Publish generated inventory proposals from trusted default-branch runs only."""
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

import inventory
import releases
import run

BRANCH = "codex/harness-inventory"
MARKER = "<!-- is-ai-agent:harness-inventory -->"
PATHS = {str(inventory.DATA), str(inventory.DOCUMENT)}


class GitHub:
    def __init__(self, repository):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Invalid repository")
        self.prefix = "repos/" + repository + "/"

    def call(self, path, method="GET", payload=None, paginate=False):
        command = ["gh", "api", self.prefix + path, "--method", method]
        if payload is not None:
            command += ["--input", "-"]
        if paginate:
            command += ["--paginate", "--slurp"]
        response = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                                  capture_output=True, text=True, timeout=60)
        if response.returncode:
            raise RuntimeError("GitHub inventory publication request failed; no response body retained")
        value = json.loads(response.stdout)
        return [item for page in value for item in page] if paginate else value


def validate_errors(errors):
    if not isinstance(errors, dict):
        raise ValueError("Invalid errors")
    for name, error in errors.items():
        if (name not in run.HARNESS or set(error) not in ({"stage", "reason"}, {"stage", "reason", "version"}) or error["stage"] not in inventory.STAGES
                or error["reason"] not in {"missing_or_duplicate_artifact", "unverified_execution", "invalid_or_incomplete_evidence"}):
            raise ValueError("Invalid error fields")
        if error.get("version") is not None:
            releases.exact_version(error["version"])


def publish(api, old, new, errors, runs, *, default_branch, tested_sha, run_url):
    inventory.validate_document(old)
    inventory.validate_document(new)
    validate_errors(errors)
    inventory.validate_runs(runs)
    if not re.fullmatch(inventory.URL, run_url) or not re.fullmatch(r"[0-9a-f]{40}", tested_sha):
        raise ValueError("Invalid publication provenance")
    for name in run.HARNESS:
        if name in errors:
            if new.get(name) != old.get(name):
                raise ValueError("Failed probes must retain previous inventory")
        elif name not in new or name not in runs:
            raise ValueError("Missing harness or run without a reported failure")
    changes = inventory.difference(old, new)
    alerts = {name: result for name, result in runs.items() if result["outcome"] != "unchanged"}
    # Prevent a stale weekly result from proposing updates against newer code.
    base = api.call("git/ref/heads/" + quote(default_branch, safe=""))["object"]["sha"]
    if base != tested_sha:
        raise ValueError("Default branch advanced; rerun the inventory workflow")
    owner = api.prefix.split("/")[1]
    prs = api.call("pulls?state=open&head=" + quote(owner + ":" + BRANCH, safe="") + "&per_page=100")
    if len(prs) > 1 or any(MARKER not in (p.get("body") or "") or p["user"]["login"] != "github-actions[bot]" for p in prs):
        raise ValueError("Inventory branch has an unrelated pull request")
    pr_url = None
    if changes:
        refs = api.call("git/matching-refs/heads/" + quote(BRANCH, safe=""))
        exact = [r for r in refs if r["ref"] == "refs/heads/" + BRANCH]
        branch_sha = exact[0]["object"]["sha"] if exact else None
        if branch_sha:
            comparison = api.call("compare/" + base + "..." + branch_sha)
            if any(f["filename"] not in PATHS for f in comparison.get("files", [])):
                raise ValueError("Inventory branch contains changes outside generated files")
        tree = api.call("git/commits/" + base)["tree"]["sha"]
        content = {str(inventory.DATA): json.dumps(new, indent=2, sort_keys=True) + "\n",
                   str(inventory.DOCUMENT): inventory.render(new)}
        tree = api.call("git/trees", "POST", {"base_tree": tree, "tree": [
            {"path": path, "mode": "100644", "type": "blob", "content": value} for path, value in content.items()]})["sha"]
        # Existing proposals are updated by a fast-forward merge commit. No
        # force push, and no checkout or execution of downloaded artifact code.
        parents = list(dict.fromkeys([branch_sha, base])) if branch_sha else [base]
        commit = api.call("git/commits", "POST", {"message": "Refresh observed harness environment inventory",
                                                   "tree": tree, "parents": parents})["sha"]
        if branch_sha:
            api.call("git/refs/heads/" + quote(BRANCH, safe=""), "PATCH", {"sha": commit, "force": False})
        else:
            api.call("git/refs", "POST", {"ref": "refs/heads/" + BRANCH, "sha": commit})
        body = MARKER + "\n\n" + inventory.report_markdown(changes, errors, run_url, runs)
        body += "\nThis proposal changes only the generated inventory and reference sheet. Merging it records observations; it does not approve any detector rule.\n"
        if prs:
            pr = api.call("pulls/" + str(prs[0]["number"]), "PATCH", {"body": body})
        else:
            pr = api.call("pulls", "POST", {"title": "Refresh harness environment inventory", "head": BRANCH,
                                               "base": default_branch, "body": body})
        pr_url = pr["html_url"]
    elif prs and not errors:
        # Latest observations returned to main's inventory while a proposal was
        # pending. Do not leave an obsolete inventory proposal open.
        api.call("pulls/" + str(prs[0]["number"]), "PATCH", {"state": "closed"})
    if changes or alerts or errors:
        digest = hashlib.sha256(json.dumps({"changes": changes, "errors": errors, "alerts": alerts}, sort_keys=True).encode()).hexdigest()
        marker = "<!-- is-ai-agent:harness-delta:" + digest + " -->"
        issues = api.call("issues?state=all&per_page=100", paginate=True)
        existing = [issue for issue in issues if "pull_request" not in issue
                    and issue["user"]["login"] == "github-actions[bot]" and marker in (issue.get("body") or "")]
        body = marker + "\n\n" + inventory.report_markdown(changes, errors, run_url, runs)
        if pr_url:
            body += "\n[Inventory proposal](" + pr_url + ")\n"
        if existing:
            if existing[0]["state"] == "open":
                api.call("issues/" + str(existing[0]["number"]), "PATCH", {"body": body})
            # Closed issues are treated as acknowledged; never reopen weekly.
        else:
            api.call("issues", "POST", {"title": "Harness observations changed — review required", "body": body})
    return {"changes": len(changes), "alerts": len(set(changes) | set(alerts) | set(errors)), "pull_request": pr_url}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("GITHUB_EVENT_NAME") not in {"schedule", "workflow_dispatch"}:
        raise ValueError("Publishing is restricted to trusted scheduled/manual runs")
    api = GitHub(os.environ["GITHUB_REPOSITORY"])
    default = api.call("")["default_branch"]
    if os.environ.get("GITHUB_REF") != "refs/heads/" + default:
        raise ValueError("Publishing is restricted to the default branch")
    old = json.loads((run.ROOT / inventory.DATA).read_text()) if (run.ROOT / inventory.DATA).exists() else inventory.empty()
    new = json.loads((args.artifacts / "observed.json").read_text())
    delta = json.loads((args.artifacts / "delta.json").read_text())
    run_url = f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    result = publish(api, old, new, delta["errors"], delta["runs"], default_branch=default, tested_sha=os.environ["GITHUB_SHA"], run_url=run_url)
    print(json.dumps(result))


if __name__ == "__main__":
    raise SystemExit(main())
