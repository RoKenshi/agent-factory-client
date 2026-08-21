#!/usr/bin/env python3
"""Publish one verified Agent Factory prerelease without GitHub Actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPOSITORY = "RoKenshi/agent-factory-client"
CONFIRMATION_ENV = "AGENT_FACTORY_PUBLISH_CONFIRM"
VERSION_RE = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")


class PublishError(RuntimeError):
    """A release precondition failed without publishing anything."""


@dataclass(frozen=True, slots=True)
class ReleasePlan:
    version: str
    tag: str
    staging: Path
    repository: str
    assets: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class PreparedRelease:
    plan: ReleasePlan
    client_revision: str
    asset_digests: tuple[tuple[str, str], ...]

    @property
    def confirmation(self) -> str:
        return (
            f"publish:{self.plan.repository}:{self.plan.tag}:"
            f"{self.client_revision}"
        )


def _artifact_names(version: str) -> tuple[str, ...]:
    return (
        f"agent-factory-v{version}-linux-x86_64.tar.gz",
        f"agent-factory-v{version}-linux-arm64.tar.gz",
        f"agent-factory-v{version}-macos-x86_64.zip",
        f"agent-factory-v{version}-macos-arm64.zip",
        f"agent-factory-v{version}-windows-x86_64.zip",
        "SHA256SUMS",
        "SHA256SUMS.sig",
    )


def _validate_version_and_tag(version: str, tag: str) -> None:
    if VERSION_RE.fullmatch(version) is None:
        raise PublishError("version must be a stable SemVer core such as 0.1.3")
    expected = f"v{version}"
    if tag != expected:
        raise PublishError(
            f"tag must exactly equal artifact version {expected}; prerelease is GitHub metadata"
        )


def _validate_repository(repository: str) -> None:
    parts = repository.split("/")
    if len(parts) != 2 or any(
        not part or re.fullmatch(r"[A-Za-z0-9_.-]+", part) is None for part in parts
    ):
        raise PublishError("repository must use the OWNER/REPO form")


def build_plan(
    *,
    version: str,
    tag: str,
    staging: Path,
    repository: str = DEFAULT_REPOSITORY,
) -> ReleasePlan:
    _validate_version_and_tag(version, tag)
    _validate_repository(repository)
    resolved = staging.expanduser().resolve()
    if not resolved.is_dir():
        raise PublishError(f"staging directory does not exist: {resolved}")

    expected = _artifact_names(version)
    actual = {path.name for path in resolved.iterdir()}
    missing = sorted(set(expected) - actual)
    unexpected = sorted(actual - set(expected))
    if missing:
        raise PublishError("staging is missing required files: " + ", ".join(missing))
    if unexpected:
        raise PublishError("staging contains unexpected files: " + ", ".join(unexpected))

    assets = tuple(resolved / name for name in expected)
    invalid = [path.name for path in assets if path.is_symlink() or not path.is_file()]
    if invalid:
        raise PublishError(
            "release assets must be regular non-symlink files: " + ", ".join(invalid)
        )
    return ReleasePlan(
        version=version,
        tag=tag,
        staging=resolved,
        repository=repository,
        assets=assets,
    )


def run_command(
    command: list[str],
    *,
    check: bool = True,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            check=check,
            capture_output=capture_output,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        executable = command[0] if command else "command"
        raise PublishError(f"{executable} release preflight failed") from error


def _output(command: list[str]) -> str:
    return run_command(command).stdout.strip()


def _require_tools() -> None:
    missing = [name for name in ("git", "gh", "sh") if shutil.which(name) is None]
    if missing:
        raise PublishError("missing required tools: " + ", ".join(missing))


def _repository_from_remote(url: str) -> str:
    value = url.strip()
    if value.startswith("git@github.com:"):
        path = value.removeprefix("git@github.com:")
    else:
        parsed = urlsplit(value)
        if parsed.scheme not in {"https", "ssh"} or parsed.hostname != "github.com":
            raise PublishError("origin must point to github.com")
        path = parsed.path.lstrip("/")
    normalized = path.removesuffix(".git").strip("/")
    _validate_repository(normalized)
    return normalized


def _assert_local_checkout(plan: ReleasePlan) -> str:
    branch = _output(["git", "branch", "--show-current"])
    if branch != "main":
        raise PublishError(f"publishing requires branch main, current branch is {branch or 'detached'}")
    if _output(["git", "status", "--porcelain", "--untracked-files=all"]):
        raise PublishError("publishing requires a clean checkout including untracked files")
    remote = _repository_from_remote(_output(["git", "remote", "get-url", "origin"]))
    if remote.casefold() != plan.repository.casefold():
        raise PublishError(
            f"origin points to {remote}, expected publisher repository {plan.repository}"
        )
    return _output(["git", "rev-parse", "HEAD"])


def _is_not_found(result: subprocess.CompletedProcess[str]) -> bool:
    rendered = f"{result.stdout}\n{result.stderr}".casefold()
    return "release not found" in rendered or "not found" in rendered or "http 404" in rendered


def _ensure_release_absent(plan: ReleasePlan) -> None:
    tag = run_command(
        ["git", "show-ref", "--verify", "--quiet", f"refs/tags/{plan.tag}"],
        check=False,
    )
    if tag.returncode == 0:
        raise PublishError(f"tag already exists and will not be moved: {plan.tag}")
    if tag.returncode != 1:
        raise PublishError("could not prove that the release tag is absent")

    release = run_command(
        ["gh", "release", "view", plan.tag, "--repo", plan.repository],
        check=False,
    )
    if release.returncode == 0:
        raise PublishError(f"release already exists and will not be replaced: {plan.tag}")
    if not _is_not_found(release):
        raise PublishError("could not prove that the GitHub release is absent")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _asset_digests(assets: tuple[Path, ...]) -> tuple[tuple[str, str], ...]:
    return tuple((path.name, _sha256(path)) for path in assets)


def prepare_release(plan: ReleasePlan) -> PreparedRelease:
    """Run every local and read-only remote preflight before publication."""
    _require_tools()
    initial_revision = _assert_local_checkout(plan)
    run_command(["git", "fetch", "--prune", "--tags", "origin"], capture_output=False)
    revision = _assert_local_checkout(plan)
    origin_revision = _output(["git", "rev-parse", "origin/main"])
    if revision != origin_revision:
        raise PublishError("HEAD must exactly match freshly fetched origin/main")
    if revision != initial_revision:
        raise PublishError("checkout revision changed during release preflight")

    run_command(["gh", "auth", "status", "--hostname", "github.com"], capture_output=False)
    resolved_repository = _output(
        [
            "gh",
            "repo",
            "view",
            plan.repository,
            "--json",
            "nameWithOwner",
            "--jq",
            ".nameWithOwner",
        ]
    )
    if resolved_repository.casefold() != plan.repository.casefold():
        raise PublishError(
            f"GitHub resolved {resolved_repository!r}, expected {plan.repository!r}"
        )
    _ensure_release_absent(plan)

    run_command(
        ["sh", str(ROOT / "tools" / "release-check.sh"), plan.version, str(plan.staging)],
        capture_output=False,
    )
    if _assert_local_checkout(plan) != revision:
        raise PublishError("checkout changed while the release bundle was verified")
    return PreparedRelease(
        plan=plan,
        client_revision=revision,
        asset_digests=_asset_digests(plan.assets),
    )


def _read_release(plan: ReleasePlan) -> dict[str, object]:
    raw = _output(
        [
            "gh",
            "release",
            "view",
            plan.tag,
            "--repo",
            plan.repository,
            "--json",
            "tagName,isDraft,isPrerelease,targetCommitish,assets,url",
        ]
    )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise PublishError("GitHub returned invalid release metadata") from error
    if not isinstance(payload, dict):
        raise PublishError("GitHub release metadata must be an object")
    return payload


def _latest_tag(repository: str) -> str | None:
    result = run_command(
        [
            "gh",
            "api",
            f"repos/{repository}/releases/latest",
            "--jq",
            ".tag_name",
        ],
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    if _is_not_found(result):
        return None
    raise PublishError("could not verify the repository's latest release")


def _quarantine_release(plan: ReleasePlan) -> None:
    run_command(
        [
            "gh",
            "release",
            "edit",
            plan.tag,
            "--repo",
            plan.repository,
            "--draft=true",
            "--prerelease=true",
            "--latest=false",
        ],
        check=False,
        capture_output=False,
    )


def _verify_published_release(prepared: PreparedRelease) -> str:
    plan = prepared.plan
    try:
        payload = _read_release(plan)
        latest_tag = _latest_tag(plan.repository)
    except PublishError as error:
        _quarantine_release(plan)
        raise PublishError(
            "published release state could not be verified and was quarantined"
        ) from error
    assets = payload.get("assets")
    names = (
        sorted(
            str(asset.get("name", ""))
            for asset in assets
            if isinstance(asset, dict)
        )
        if isinstance(assets, list)
        else []
    )
    expected = sorted(path.name for path in plan.assets)
    valid = (
        payload.get("tagName") == plan.tag
        and payload.get("isDraft") is False
        and payload.get("isPrerelease") is True
        and payload.get("targetCommitish") == prepared.client_revision
        and names == expected
    )
    if not valid or latest_tag == plan.tag:
        _quarantine_release(plan)
        raise PublishError("published release failed the prerelease safety audit and was quarantined")
    return str(payload.get("url") or "")


def _copy_verified_assets(prepared: PreparedRelease, destination: Path) -> tuple[Path, ...]:
    current = _asset_digests(prepared.plan.assets)
    if current != prepared.asset_digests:
        raise PublishError("release assets changed after verification")
    copied: list[Path] = []
    for source in prepared.plan.assets:
        target = destination / source.name
        shutil.copyfile(source, target)
        copied.append(target)
    snapshot = tuple(copied)
    if _asset_digests(snapshot) != prepared.asset_digests:
        raise PublishError("release asset snapshot does not match the verified bundle")
    return snapshot


def publish_release(prepared: PreparedRelease) -> str:
    plan = prepared.plan
    if os.environ.get(CONFIRMATION_ENV) != prepared.confirmation:
        raise PublishError(
            f"refusing publication: set {CONFIRMATION_ENV}={prepared.confirmation} exactly"
        )
    revision = _assert_local_checkout(plan)
    if revision != prepared.client_revision or _output(["git", "rev-parse", "origin/main"]) != revision:
        raise PublishError("checkout no longer matches the prepared origin/main revision")
    _ensure_release_absent(plan)

    with tempfile.TemporaryDirectory(prefix="agent-factory-publish-") as temporary:
        snapshot = _copy_verified_assets(prepared, Path(temporary))
        notes = (
            f"Agent Factory {plan.tag} prerelease.\n\n"
            "This release is intentionally a prerelease and is never marked latest or GA.\n"
            f"Client publisher revision: `{prepared.client_revision}`."
        )
        run_command(
            [
                "gh",
                "release",
                "create",
                plan.tag,
                *(str(path) for path in snapshot),
                "--repo",
                plan.repository,
                "--target",
                prepared.client_revision,
                "--title",
                f"Agent Factory {plan.tag} prerelease",
                "--notes",
                notes,
                "--prerelease",
                "--latest=false",
            ],
            capture_output=False,
        )
    return _verify_published_release(prepared)


def print_plan(prepared: PreparedRelease) -> None:
    plan = prepared.plan
    print("Agent Factory local prerelease publisher")
    print("mode: dry-run; no GitHub release or tag was created")
    print(f"repository: {plan.repository}")
    print(f"tag: {plan.tag}")
    print(f"version: {plan.version}")
    print(f"client revision: {prepared.client_revision}")
    print(f"verified assets: {len(plan.assets)}")
    print("release state: prerelease=true, latest=false")
    print("private signing key: not read or modified by this publisher")
    print("to execute, rerun with --execute and set exactly:")
    print(f"  {CONFIRMATION_ENV}={prepared.confirmation}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="artifact version, for example 0.1.3")
    parser.add_argument(
        "--tag", required=True, help="exact immutable artifact tag, for example v0.1.3"
    )
    parser.add_argument("--staging", required=True, type=Path)
    parser.add_argument("--repo", default=DEFAULT_REPOSITORY)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="create the prerelease after exact environment confirmation",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        plan = build_plan(
            version=arguments.version,
            tag=arguments.tag,
            staging=arguments.staging,
            repository=arguments.repo,
        )
        prepared = prepare_release(plan)
        print_plan(prepared)
        if arguments.execute:
            url = publish_release(prepared)
            print(f"published prerelease: {url or plan.tag}")
        return 0
    except PublishError as error:
        print(f"publish failed safely: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
