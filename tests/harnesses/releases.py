"""Resolve public release selectors to exact, recorded build specifications."""
import copy
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import urllib.request
from urllib.parse import quote, urlsplit

VERSION = r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_):
        return None


def read_url(url, limit=16 * 1024 * 1024):
    if urlsplit(url).scheme != "https":
        raise ValueError("Release metadata must use HTTPS")
    headers = {"User-Agent": "is-ai-agent-harness-tests"}
    opener = urllib.request.build_opener()
    # The Actions token stays in the host resolver, never in a build or CLI.
    # Do not forward it to release assets, npm, raw content, or redirects.
    if urlsplit(url).hostname == "api.github.com":
        opener = urllib.request.build_opener(NoRedirect)
        if token := os.environ.get("GH_TOKEN"):
            headers["Authorization"] = "Bearer " + token
        elif shutil.which("gh"):
            # Use the existing CLI login locally without reading/exporting its
            # credential. Anonymous GitHub metadata requests are rate limited.
            result = subprocess.run(["gh", "api", urlsplit(url).path.lstrip("/")],
                                    capture_output=True, timeout=60, check=False)
            if result.returncode or len(result.stdout) > limit:
                raise OSError("GitHub release metadata unavailable")
            return result.stdout
    with opener.open(urllib.request.Request(url, headers=headers), timeout=60) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Release metadata exceeds limit")
    return data


def json_url(url):
    return json.loads(read_url(url))


def exact_version(value):
    if not isinstance(value, str) or not re.fullmatch(VERSION, value):
        raise ValueError("Expected an exact release version")
    return value


def release_asset(release, name):
    asset = next(a for a in release["assets"] if a["name"] == name)
    url = asset["browser_download_url"]
    if not url.startswith("https://github.com/") or urlsplit(url).query:
        raise ValueError("Unexpected release asset URL")
    digest = asset.get("digest") or ""
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        digest = "sha256:" + hashlib.sha256(read_url(url, 512 * 1024 * 1024)).hexdigest()
    return {"url": url, "sha256": digest.removeprefix("sha256:")}


def resolve(harness, pinned, selector="latest"):
    """Keep the reviewed detection contract; replace only release metadata."""
    spec = copy.deepcopy(pinned)
    spec.pop("compatibility_versions", None)
    if selector != "latest":
        exact_version(selector)
    if harness in ("goose", "vtcode", "hermes-agent"):
        repos = {"goose": "aaif-goose/goose", "vtcode": "vinhnx/VTCode",
                 "hermes-agent": "NousResearch/hermes-agent"}
        repo = repos[harness]
        if selector != "latest" and harness == "hermes-agent":
            raise ValueError("Hermes release tags and package versions differ; use latest or pinned source metadata")
        tag = ("v" if harness == "goose" else "") + selector
        suffix = "latest" if selector == "latest" else "tags/" + quote(tag, safe="")
        release = json_url(f"https://api.github.com/repos/{repo}/releases/{suffix}")
        if release.get("draft") or (selector == "latest" and release.get("prerelease")):
            raise ValueError("Expected a published stable GitHub release")
        if harness == "hermes-agent":
            commit = json_url(f"https://api.github.com/repos/{repo}/commits/{quote(release['tag_name'], safe='')}")["sha"]
            if not re.fullmatch(r"[0-9a-f]{40}", commit):
                raise ValueError("Invalid source commit")
            project = read_url(f"https://raw.githubusercontent.com/{repo}/{commit}/pyproject.toml").decode()
            section = re.search(r"(?ms)^\[project\]\s*\n(.*?)(?=^\[|\Z)", project)[1]
            spec["version"] = exact_version(re.search(r'^version\s*=\s*"([^"]+)"', section, re.M)[1])
            url = f"https://codeload.github.com/{repo}/tar.gz/{commit}"
            digest = (pinned["source"]["sha256"] if url == pinned["source"]["url"]
                      else hashlib.sha256(read_url(url, 512 * 1024 * 1024)).hexdigest())
            spec["source"] = {"url": url, "sha256": digest}
        else:
            version = exact_version(release["tag_name"].removeprefix("v"))
            if selector != "latest" and version != selector:
                raise ValueError("Resolved release differs from requested version")
            spec["version"] = version
            spec["assets"] = {}
            for arch, target in [("arm64", "aarch64"), ("x64", "x86_64")]:
                libc = "gnu" if harness == "vtcode" and arch == "arm64" else "musl"
                name = (f"goose-{target}-unknown-linux-musl.tar.gz" if harness == "goose"
                        else f"vtcode-{version}-{target}-unknown-linux-{libc}.tar.gz")
                spec["assets"][arch] = {**release_asset(release, name), "arch": target}
        spec["release_tag"] = release["tag_name"]
    else:
        package = quote(spec["package"], safe="")
        metadata = json_url(f"https://registry.npmjs.org/{package}/{quote(selector, safe='')}")
        spec["version"] = exact_version(metadata["version"])
        if selector != "latest" and spec["version"] != selector:
            raise ValueError("Resolved release differs from requested version")
        # The installer checks this metadata again; npm verifies the download.
        integrity = metadata["dist"]["integrity"]
        if not re.fullmatch(r"sha512-[A-Za-z0-9+/=]+", integrity):
            raise ValueError("Unexpected npm integrity metadata")
        spec["npm_integrity"] = integrity
        if harness == "junie":
            content = json_url("https://api.github.com/repos/JetBrains/junie/contents/update-info.jsonl")
            info = base64.b64decode(content["content"]).decode()
            build = spec["version"].removesuffix(".0")
            record = next(json.loads(line) for line in info.splitlines()
                          if json.loads(line).get("version") == build)
            marketing = record["marketing"]
            if not re.fullmatch(r"[0-9.]+", marketing):
                raise ValueError("Unexpected Junie version label")
            spec["reported_version"] = f"{marketing} ({build})"
    return spec


def pinned_spec(spec, version):
    """Select an explicitly reviewed compatibility case without network access."""
    exact_version(version)
    if version == spec["version"]:
        return copy.deepcopy(spec)
    extra = next((x for x in spec.get("compatibility_versions", []) if x["version"] == version), None)
    if extra is not None:
        for metadata in ("source", "assets", "reported_version"):
            if metadata in spec and metadata not in extra:
                raise ValueError("Compatibility case needs matching release metadata")
        return {**copy.deepcopy(spec), **copy.deepcopy(extra)}
    if any(key in spec for key in ("assets", "source", "reported_version")):
        raise ValueError("This adapter needs matching release metadata; update its manifest entry instead")
    return {**copy.deepcopy(spec), "version": version}


def matrix(harnesses):
    cases = []
    for name, spec in harnesses.items():
        versions = [spec["version"], *(x["version"] for x in spec.get("compatibility_versions", []))]
        if len(versions) != len(set(versions)):
            raise ValueError("Duplicate compatibility version")
        for version in versions:
            pinned_spec(spec, version)
            cases.append({"harness": name, "version": version})
    return {"include": cases}
