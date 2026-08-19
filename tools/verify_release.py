#!/usr/bin/env python3
"""Verify a complete Agent Factory release bundle before it is published."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
import unicodedata
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path


VERSION_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z.+-]*$")
CHECKSUM_RE = re.compile(r"^([0-9a-fA-F]{64})[ \t]+\*?(\S+)$")
FULL_SOURCE_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_MANIFEST_BYTES = 64 * 1024
MAX_ARCHIVE_MEMBERS = 100_000
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class Artifact:
    platform: str
    architecture: str
    extension: str

    def filename(self, version: str) -> str:
        return f"agent-factory-v{version}-{self.platform}-{self.architecture}.{self.extension}"

    def root(self, version: str) -> str:
        return f"agent-factory-v{version}-{self.platform}-{self.architecture}"

    @property
    def executable(self) -> str:
        return "agent-factory.exe" if self.platform == "windows" else "agent-factory"


SUPPORTED_ARTIFACTS = (
    Artifact("linux", "x86_64", "tar.gz"),
    Artifact("linux", "arm64", "tar.gz"),
    Artifact("macos", "x86_64", "zip"),
    Artifact("macos", "arm64", "zip"),
    Artifact("windows", "x86_64", "zip"),
)


class ReleaseVerificationError(RuntimeError):
    pass


class ReleaseSource:
    def __init__(self, *, directory: Path | None, base_url: str | None) -> None:
        if (directory is None) == (base_url is None):
            raise ReleaseVerificationError("select exactly one release source")
        if base_url is not None and not base_url.startswith("https://"):
            raise ReleaseVerificationError("published release base URL must use HTTPS")
        self.directory = directory
        self.base_url = base_url.rstrip("/") if base_url else None

    def read(self, name: str) -> bytes:
        if self.directory is not None:
            path = self.directory / name
            if path.is_symlink() or not path.is_file():
                raise ReleaseVerificationError(f"missing release file: {name}")
            return path.read_bytes()
        assert self.base_url is not None
        try:
            with urllib.request.urlopen(f"{self.base_url}/{name}", timeout=30) as response:
                return response.read()
        except Exception as exc:
            raise ReleaseVerificationError(f"cannot download release file: {name}: {exc}") from exc


def _safe_member(name: str, root: str) -> bool:
    if (
        not name
        or "\\" in name
        or any(ord(character) < 32 or ord(character) == 127 for character in name)
    ):
        return False
    parts = name.split("/")
    if parts[-1] == "":
        parts.pop()
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return False
    return parts[0] == root


def _record_member_path(
    name: str,
    artifact_name: str,
    exact_paths: set[str],
    portable_paths: dict[str, str],
) -> None:
    if name in exact_paths:
        raise ReleaseVerificationError(
            f"{artifact_name} contains a duplicate member path: {name}"
        )
    exact_paths.add(name)
    portable = "/".join(
        unicodedata.normalize("NFC", part).casefold().rstrip(" .")
        for part in name.rstrip("/").split("/")
    )
    previous = portable_paths.get(portable)
    if previous is not None:
        raise ReleaseVerificationError(
            f"{artifact_name} contains a portable path collision: {previous} and {name}"
        )
    portable_paths[portable] = name


def _verify_manifest(data: bytes, artifact: Artifact, version: str) -> str:
    name = artifact.filename(version)
    if len(data) > MAX_MANIFEST_BYTES:
        raise ReleaseVerificationError(f"{name} MANIFEST.json is too large")
    try:
        manifest = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseVerificationError(f"{name} has an invalid MANIFEST.json") from exc
    if not isinstance(manifest, dict):
        raise ReleaseVerificationError(f"{name} MANIFEST.json must be a JSON object")

    expected_platform = f"{artifact.platform}-{artifact.architecture}"
    expected_values = {
        "name": "agent-factory",
        "version": version,
        "platform": expected_platform,
        "executable": artifact.executable,
    }
    for field, expected in expected_values.items():
        if manifest.get(field) != expected:
            raise ReleaseVerificationError(
                f"{name} MANIFEST.json has {field}={manifest.get(field)!r}; "
                f"expected {expected!r}"
            )
    schema_version = manifest.get("schema_version")
    if type(schema_version) is not int or schema_version != 1:
        raise ReleaseVerificationError(f"{name} MANIFEST.json requires schema_version=1")
    python_version = manifest.get("python")
    if not isinstance(python_version, str) or not python_version.strip():
        raise ReleaseVerificationError(
            f"{name} MANIFEST.json python must be a non-empty string"
        )
    if manifest.get("platform_signature") not in {"adhoc", "none"}:
        raise ReleaseVerificationError(
            f"{name} MANIFEST.json has unsupported platform_signature"
        )
    if manifest.get("releasable") is not True:
        raise ReleaseVerificationError(f"{name} MANIFEST.json is not releasable")
    if manifest.get("source_dirty") is not False:
        raise ReleaseVerificationError(f"{name} MANIFEST.json is dirty")

    source_commit = manifest.get("source_commit")
    source_revision = manifest.get("source_revision")
    if not isinstance(source_commit, str) or FULL_SOURCE_REVISION_RE.fullmatch(
        source_commit
    ) is None:
        raise ReleaseVerificationError(
            f"{name} MANIFEST.json source_commit must be a lowercase 40-character SHA"
        )
    if not isinstance(source_revision, str) or FULL_SOURCE_REVISION_RE.fullmatch(
        source_revision
    ) is None:
        raise ReleaseVerificationError(
            f"{name} MANIFEST.json source_revision must be a lowercase 40-character SHA"
        )
    if source_commit != source_revision:
        raise ReleaseVerificationError(
            f"{name} MANIFEST.json source_commit and source_revision differ"
        )
    return source_revision


def _verify_zip(data: bytes, artifact: Artifact, version: str) -> str:
    root = artifact.root(version)
    executable = f"{root}/{artifact.executable}"
    manifest_name = f"{root}/MANIFEST.json"
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            found_executable = False
            manifest_members: list[zipfile.ZipInfo] = []
            members = archive.infolist()
            if len(members) > MAX_ARCHIVE_MEMBERS:
                raise ReleaseVerificationError(
                    f"{artifact.filename(version)} contains too many members"
                )
            total_size = sum(member.file_size for member in members if not member.is_dir())
            if total_size > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                raise ReleaseVerificationError(
                    f"{artifact.filename(version)} exceeds the uncompressed size limit"
                )
            exact_paths: set[str] = set()
            portable_paths: dict[str, str] = {}
            for member in members:
                if not _safe_member(member.filename, root):
                    raise ReleaseVerificationError(
                        f"{artifact.filename(version)} contains unsafe path: {member.filename}"
                    )
                _record_member_path(
                    member.filename,
                    artifact.filename(version),
                    exact_paths,
                    portable_paths,
                )
                if member.flag_bits & 0x1:
                    raise ReleaseVerificationError(
                        f"{artifact.filename(version)} contains an encrypted member"
                    )
                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise ReleaseVerificationError(
                        f"{artifact.filename(version)} contains a symbolic link: {member.filename}"
                    )
                file_type = stat.S_IFMT(mode)
                if mode and not member.is_dir() and file_type not in (0, stat.S_IFREG):
                    raise ReleaseVerificationError(
                        f"{artifact.filename(version)} contains a special file: {member.filename}"
                    )
                if member.filename == executable and not member.is_dir():
                    found_executable = True
                    if artifact.platform != "windows" and mode and not mode & 0o111:
                        raise ReleaseVerificationError(
                            f"{artifact.filename(version)} executable has no execute bit"
                        )
                if member.filename == manifest_name and not member.is_dir():
                    manifest_members.append(member)
            if len(manifest_members) != 1:
                raise ReleaseVerificationError(
                    f"{artifact.filename(version)} must contain exactly one {manifest_name}"
                )
            manifest_member = manifest_members[0]
            if manifest_member.file_size > MAX_MANIFEST_BYTES:
                raise ReleaseVerificationError(
                    f"{artifact.filename(version)} MANIFEST.json is too large"
                )
            bad_member = archive.testzip()
            if bad_member is not None:
                raise ReleaseVerificationError(
                    f"{artifact.filename(version)} failed ZIP CRC validation: {bad_member}"
                )
            manifest_data = archive.read(manifest_member)
    except ReleaseVerificationError:
        raise
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise ReleaseVerificationError(
            f"invalid ZIP archive: {artifact.filename(version)}"
        ) from exc
    if not found_executable:
        raise ReleaseVerificationError(
            f"{artifact.filename(version)} is missing {executable}"
        )
    return _verify_manifest(manifest_data, artifact, version)


def _verify_tar(data: bytes, artifact: Artifact, version: str) -> str:
    root = artifact.root(version)
    executable = f"{root}/{artifact.executable}"
    manifest_name = f"{root}/MANIFEST.json"
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            found_executable = False
            manifest_members: list[tarfile.TarInfo] = []
            member_count = 0
            total_size = 0
            exact_paths: set[str] = set()
            portable_paths: dict[str, str] = {}
            for member in archive:
                member_count += 1
                if member_count > MAX_ARCHIVE_MEMBERS:
                    raise ReleaseVerificationError(
                        f"{artifact.filename(version)} contains too many members"
                    )
                if not _safe_member(member.name, root):
                    raise ReleaseVerificationError(
                        f"{artifact.filename(version)} contains unsafe path: {member.name}"
                    )
                _record_member_path(
                    member.name,
                    artifact.filename(version),
                    exact_paths,
                    portable_paths,
                )
                if not (member.isfile() or member.isdir()):
                    raise ReleaseVerificationError(
                        f"{artifact.filename(version)} contains a link or special file: "
                        f"{member.name}"
                    )
                if member.isfile():
                    if member.size < 0:
                        raise ReleaseVerificationError(
                            f"{artifact.filename(version)} contains a negative member size"
                        )
                    total_size += member.size
                    if total_size > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                        raise ReleaseVerificationError(
                            f"{artifact.filename(version)} exceeds the uncompressed size limit"
                        )
                if member.name == executable and member.isfile():
                    found_executable = True
                    if not member.mode & 0o111:
                        raise ReleaseVerificationError(
                            f"{artifact.filename(version)} executable has no execute bit"
                        )
                if member.name == manifest_name and member.isfile():
                    manifest_members.append(member)
            if len(manifest_members) != 1:
                raise ReleaseVerificationError(
                    f"{artifact.filename(version)} must contain exactly one {manifest_name}"
                )
            manifest_member = manifest_members[0]
            if manifest_member.size > MAX_MANIFEST_BYTES:
                raise ReleaseVerificationError(
                    f"{artifact.filename(version)} MANIFEST.json is too large"
                )
            manifest_file = archive.extractfile(manifest_member)
            if manifest_file is None:
                raise ReleaseVerificationError(
                    f"{artifact.filename(version)} cannot read {manifest_name}"
                )
            manifest_data = manifest_file.read(MAX_MANIFEST_BYTES + 1)
    except ReleaseVerificationError:
        raise
    except (EOFError, OSError, tarfile.TarError) as exc:
        raise ReleaseVerificationError(
            f"invalid tar archive: {artifact.filename(version)}"
        ) from exc
    if not found_executable:
        raise ReleaseVerificationError(
            f"{artifact.filename(version)} is missing {executable}"
        )
    return _verify_manifest(manifest_data, artifact, version)


def _verify_local_staging(directory: Path, expected_names: set[str]) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise ReleaseVerificationError(f"release staging directory not found: {directory}")
    try:
        entries = list(directory.iterdir())
    except OSError as exc:
        raise ReleaseVerificationError(f"cannot inspect release staging directory: {exc}") from exc
    invalid = sorted(
        entry.name for entry in entries if entry.is_symlink() or not entry.is_file()
    )
    if invalid:
        raise ReleaseVerificationError(
            "release staging contains non-regular files: " + ", ".join(invalid)
        )
    actual_names = {entry.name for entry in entries}
    if len(entries) != len(actual_names):
        raise ReleaseVerificationError("release staging contains duplicate file names")
    missing = sorted(expected_names - actual_names)
    unexpected = sorted(actual_names - expected_names)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unexpected:
            details.append("unexpected " + ", ".join(unexpected))
        raise ReleaseVerificationError(
            "release staging must contain exactly seven release files: " + "; ".join(details)
        )


def _parse_checksums(data: bytes) -> dict[str, str]:
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ReleaseVerificationError("SHA256SUMS is not ASCII") from exc
    checksums: dict[str, str] = {}
    for line in text.splitlines():
        match = CHECKSUM_RE.fullmatch(line)
        if match is None:
            raise ReleaseVerificationError(f"invalid SHA256SUMS line: {line!r}")
        digest, name = match.groups()
        if name in checksums:
            raise ReleaseVerificationError(f"duplicate SHA256SUMS entry: {name}")
        checksums[name] = digest.lower()
    return checksums


def _verify_signature(checksums: bytes, signature: bytes, public_key: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="agent-factory-release-verify-") as temporary:
        root = Path(temporary)
        checksums_path = root / "SHA256SUMS"
        signature_path = root / "SHA256SUMS.sig"
        checksums_path.write_bytes(checksums)
        signature_path.write_bytes(signature)
        result = subprocess.run(
            [
                "openssl",
                "dgst",
                "-sha256",
                "-verify",
                str(public_key),
                "-signature",
                str(signature_path),
                str(checksums_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    if result.returncode != 0:
        raise ReleaseVerificationError("release signature verification failed")


def verify_release(source: ReleaseSource, version: str, public_key: Path) -> list[str]:
    version = version.removeprefix("v")
    if VERSION_RE.fullmatch(version) is None:
        raise ReleaseVerificationError(f"invalid release version: {version!r}")
    if not public_key.is_file():
        raise ReleaseVerificationError(f"release public key not found: {public_key}")

    expected_names = {artifact.filename(version) for artifact in SUPPORTED_ARTIFACTS}
    if source.directory is not None:
        _verify_local_staging(
            source.directory,
            expected_names | {"SHA256SUMS", "SHA256SUMS.sig"},
        )

    checksums_data = source.read("SHA256SUMS")
    signature_data = source.read("SHA256SUMS.sig")
    _verify_signature(checksums_data, signature_data, public_key)
    checksums = _parse_checksums(checksums_data)
    missing = sorted(expected_names - checksums.keys())
    unexpected = sorted(checksums.keys() - expected_names)
    if missing:
        raise ReleaseVerificationError(
            "SHA256SUMS is missing required artifacts: " + ", ".join(missing)
        )
    if unexpected:
        raise ReleaseVerificationError(
            "SHA256SUMS contains unsupported artifacts: " + ", ".join(unexpected)
        )

    verified: list[str] = []
    source_revision: str | None = None
    for artifact in SUPPORTED_ARTIFACTS:
        name = artifact.filename(version)
        data = source.read(name)
        actual = hashlib.sha256(data).hexdigest()
        if actual != checksums[name]:
            raise ReleaseVerificationError(f"SHA-256 verification failed: {name}")
        if artifact.extension == "zip":
            artifact_revision = _verify_zip(data, artifact, version)
        else:
            artifact_revision = _verify_tar(data, artifact, version)
        if source_revision is None:
            source_revision = artifact_revision
        elif artifact_revision != source_revision:
            raise ReleaseVerificationError(
                "release artifacts do not share one source revision: "
                f"{name} has {artifact_revision}, expected {source_revision}"
            )
        verified.append(name)
    return verified


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="release version, with or without v")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--directory", type=Path, help="local release staging directory")
    source.add_argument("--base-url", help="published release asset base URL")
    parser.add_argument(
        "--public-key",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "RELEASE-SIGNING-KEY.pem",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        verified = verify_release(
            ReleaseSource(directory=args.directory, base_url=args.base_url),
            args.version,
            args.public_key,
        )
    except (OSError, ReleaseVerificationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for name in verified:
        print(f"verified: {name}")
    print(f"release bundle is complete: {len(verified)} artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
