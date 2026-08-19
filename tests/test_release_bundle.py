from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.verify_release import (  # noqa: E402
    SUPPORTED_ARTIFACTS,
    Artifact,
    ReleaseSource,
    ReleaseVerificationError,
    verify_release,
)


class ReleaseBundleTest(unittest.TestCase):
    revision = "0123456789abcdef0123456789abcdef01234567"

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="agent-factory-release-test-")
        self.root = Path(self.temporary.name)
        self.release = self.root / "release"
        self.release.mkdir()
        self.private_key = self.root / "private.pem"
        self.public_key = self.root / "public.pem"
        subprocess.run(
            [
                "openssl",
                "genpkey",
                "-algorithm",
                "RSA",
                "-pkeyopt",
                "rsa_keygen_bits:2048",
                "-out",
                str(self.private_key),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "openssl",
                "pkey",
                "-in",
                str(self.private_key),
                "-pubout",
                "-out",
                str(self.public_key),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _manifest(
        self, artifact: Artifact, overrides: dict[str, object] | None = None
    ) -> bytes:
        manifest: dict[str, object] = {
            "name": "agent-factory",
            "schema_version": 1,
            "version": "1.2.3",
            "platform": f"{artifact.platform}-{artifact.architecture}",
            "executable": artifact.executable,
            "platform_signature": "adhoc" if artifact.platform == "macos" else "none",
            "python": "3.12.14",
            "releasable": True,
            "source_commit": self.revision,
            "source_dirty": False,
            "source_revision": self.revision,
        }
        manifest.update(overrides or {})
        return (json.dumps(manifest, sort_keys=True) + "\n").encode()

    def _archive(
        self,
        artifact: Artifact,
        *,
        unsafe_link: bool = False,
        include_manifest: bool = True,
        duplicate_manifest: bool = False,
        duplicate_member: bool = False,
        portable_collision: bool = False,
        dot_alias: bool = False,
        corrupt_crc: bool = False,
        manifest_overrides: dict[str, object] | None = None,
    ) -> bytes:
        root = artifact.root("1.2.3")
        executable = f"{root}/{artifact.executable}"
        manifest_name = f"{root}/MANIFEST.json"
        manifest_data = self._manifest(artifact, manifest_overrides)
        output = io.BytesIO()
        if artifact.extension == "tar.gz":
            with tarfile.open(fileobj=output, mode="w:gz") as archive:
                info = tarfile.TarInfo(executable)
                info.mode = 0o755
                info.size = 6
                archive.addfile(info, io.BytesIO(b"binary"))
                if unsafe_link:
                    link = tarfile.TarInfo(f"{root}/escape")
                    link.type = tarfile.SYMTYPE
                    link.linkname = "/tmp/escape"
                    archive.addfile(link)
                if include_manifest:
                    repetitions = 2 if duplicate_manifest else 1
                    for _ in range(repetitions):
                        manifest = tarfile.TarInfo(manifest_name)
                        manifest.mode = 0o644
                        manifest.size = len(manifest_data)
                        archive.addfile(manifest, io.BytesIO(manifest_data))
                if duplicate_member:
                    for _ in range(2):
                        duplicate = tarfile.TarInfo(f"{root}/README.txt")
                        duplicate.mode = 0o644
                        duplicate.size = 4
                        archive.addfile(duplicate, io.BytesIO(b"read"))
                if portable_collision:
                    for name in (f"{root}/Docs/Café.txt", f"{root}/docs/café.TXT"):
                        collision = tarfile.TarInfo(name)
                        collision.mode = 0o644
                        collision.size = 4
                        archive.addfile(collision, io.BytesIO(b"read"))
                if dot_alias:
                    alias = tarfile.TarInfo(f"./{root}/alias.txt")
                    alias.mode = 0o644
                    alias.size = 4
                    archive.addfile(alias, io.BytesIO(b"read"))
        else:
            with zipfile.ZipFile(output, mode="w") as archive:
                info = zipfile.ZipInfo(executable)
                info.external_attr = 0o100755 << 16
                archive.writestr(info, b"binary")
                if include_manifest:
                    manifest = zipfile.ZipInfo(manifest_name)
                    manifest.external_attr = 0o100644 << 16
                    archive.writestr(manifest, manifest_data)
                if duplicate_member:
                    for _ in range(2):
                        archive.writestr(f"{root}/README.txt", b"read")
                if portable_collision:
                    archive.writestr(f"{root}/Docs/Café.txt", b"read")
                    archive.writestr(f"{root}/docs/café.TXT", b"read")
                if dot_alias:
                    archive.writestr(f"./{root}/alias.txt", b"read")
        data = output.getvalue()
        if corrupt_crc:
            data = data.replace(b"binary", b"binarx", 1)
        return data

    def _write_bundle(
        self,
        *,
        omit: str | None = None,
        unsafe_link: str | None = None,
        missing_manifest: str | None = None,
        duplicate_manifest: str | None = None,
        duplicate_member: str | None = None,
        portable_collision: str | None = None,
        dot_alias: str | None = None,
        corrupt_crc: str | None = None,
        manifest_overrides: dict[str, dict[str, object]] | None = None,
    ) -> None:
        checksum_lines: list[str] = []
        for artifact in SUPPORTED_ARTIFACTS:
            name = artifact.filename("1.2.3")
            if name == omit:
                continue
            data = self._archive(
                artifact,
                unsafe_link=name == unsafe_link,
                include_manifest=name != missing_manifest,
                duplicate_manifest=name == duplicate_manifest,
                duplicate_member=name == duplicate_member,
                portable_collision=name == portable_collision,
                dot_alias=name == dot_alias,
                corrupt_crc=name == corrupt_crc,
                manifest_overrides=(manifest_overrides or {}).get(name),
            )
            (self.release / name).write_bytes(data)
            checksum_lines.append(f"{hashlib.sha256(data).hexdigest()}  {name}\n")
        checksums = self.release / "SHA256SUMS"
        checksums.write_text("".join(checksum_lines), encoding="ascii")
        subprocess.run(
            [
                "openssl",
                "dgst",
                "-sha256",
                "-sign",
                str(self.private_key),
                "-out",
                str(self.release / "SHA256SUMS.sig"),
                str(checksums),
            ],
            check=True,
        )

    def test_complete_bundle_passes(self) -> None:
        self._write_bundle()
        verified = verify_release(
            ReleaseSource(directory=self.release, base_url=None), "v1.2.3", self.public_key
        )
        self.assertEqual(len(verified), 5)

    def test_missing_supported_artifact_fails(self) -> None:
        missing = "agent-factory-v1.2.3-linux-arm64.tar.gz"
        self._write_bundle(omit=missing)
        with self.assertRaisesRegex(ReleaseVerificationError, "exactly seven release files"):
            verify_release(
                ReleaseSource(directory=self.release, base_url=None), "1.2.3", self.public_key
            )

    def test_link_in_tar_archive_fails(self) -> None:
        unsafe = "agent-factory-v1.2.3-linux-x86_64.tar.gz"
        self._write_bundle(unsafe_link=unsafe)
        with self.assertRaisesRegex(ReleaseVerificationError, "link or special file"):
            verify_release(
                ReleaseSource(directory=self.release, base_url=None), "1.2.3", self.public_key
            )

    def test_tampered_signature_fails(self) -> None:
        self._write_bundle()
        (self.release / "SHA256SUMS.sig").write_bytes(b"tampered")
        with self.assertRaisesRegex(ReleaseVerificationError, "signature verification failed"):
            verify_release(
                ReleaseSource(directory=self.release, base_url=None), "1.2.3", self.public_key
            )

    def test_tampered_archive_fails(self) -> None:
        self._write_bundle()
        archive = self.release / "agent-factory-v1.2.3-macos-arm64.zip"
        archive.write_bytes(archive.read_bytes() + b"tampered")
        with self.assertRaisesRegex(ReleaseVerificationError, "SHA-256 verification failed"):
            verify_release(
                ReleaseSource(directory=self.release, base_url=None), "1.2.3", self.public_key
            )

    def test_missing_root_manifest_fails(self) -> None:
        target = "agent-factory-v1.2.3-macos-x86_64.zip"
        self._write_bundle(missing_manifest=target)
        with self.assertRaisesRegex(ReleaseVerificationError, "exactly one .*MANIFEST.json"):
            verify_release(
                ReleaseSource(directory=self.release, base_url=None), "1.2.3", self.public_key
            )

    def test_duplicate_root_manifest_fails(self) -> None:
        target = "agent-factory-v1.2.3-linux-x86_64.tar.gz"
        self._write_bundle(duplicate_manifest=target)
        with self.assertRaisesRegex(ReleaseVerificationError, "duplicate member path"):
            verify_release(
                ReleaseSource(directory=self.release, base_url=None), "1.2.3", self.public_key
            )

    def test_manifest_release_contract_is_fail_closed(self) -> None:
        target = "agent-factory-v1.2.3-windows-x86_64.zip"
        cases = (
            ({"version": "1.2.4"}, "has version"),
            ({"platform": "windows-arm64"}, "has platform"),
            ({"schema_version": 2}, "requires schema_version=1"),
            ({"executable": "agent-factory"}, "has executable"),
            ({"python": ""}, "python must be"),
            ({"platform_signature": "signed"}, "unsupported platform_signature"),
            ({"releasable": False}, "is not releasable"),
            ({"source_dirty": True}, "is dirty"),
            ({"source_commit": "A" * 40}, "source_commit must be"),
            ({"source_revision": "abcd"}, "source_revision must be"),
            ({"source_revision": "f" * 40}, "source_commit and source_revision differ"),
        )
        for overrides, error in cases:
            with self.subTest(overrides=overrides):
                self._write_bundle(manifest_overrides={target: overrides})
                with self.assertRaisesRegex(ReleaseVerificationError, error):
                    verify_release(
                        ReleaseSource(directory=self.release, base_url=None),
                        "1.2.3",
                        self.public_key,
                    )

    def test_all_manifests_must_share_one_source_revision(self) -> None:
        target = "agent-factory-v1.2.3-macos-arm64.zip"
        other_revision = "f" * 40
        self._write_bundle(
            manifest_overrides={
                target: {
                    "source_commit": other_revision,
                    "source_revision": other_revision,
                }
            }
        )
        with self.assertRaisesRegex(ReleaseVerificationError, "one source revision"):
            verify_release(
                ReleaseSource(directory=self.release, base_url=None), "1.2.3", self.public_key
            )

    def test_local_staging_rejects_unexpected_file(self) -> None:
        self._write_bundle()
        (self.release / "notes.txt").write_text("not a release asset\n", encoding="utf-8")
        with self.assertRaisesRegex(ReleaseVerificationError, "exactly seven release files"):
            verify_release(
                ReleaseSource(directory=self.release, base_url=None), "1.2.3", self.public_key
            )

    def test_local_staging_rejects_symlinked_asset(self) -> None:
        self._write_bundle()
        target = self.release / "agent-factory-v1.2.3-linux-arm64.tar.gz"
        external = self.root / "external.tar.gz"
        external.write_bytes(target.read_bytes())
        target.unlink()
        target.symlink_to(external)
        with self.assertRaisesRegex(ReleaseVerificationError, "non-regular files"):
            verify_release(
                ReleaseSource(directory=self.release, base_url=None), "1.2.3", self.public_key
            )

    def test_duplicate_archive_member_fails(self) -> None:
        target = "agent-factory-v1.2.3-linux-arm64.tar.gz"
        self._write_bundle(duplicate_member=target)
        with self.assertRaisesRegex(ReleaseVerificationError, "duplicate member path"):
            verify_release(
                ReleaseSource(directory=self.release, base_url=None), "1.2.3", self.public_key
            )

    def test_unicode_casefold_portable_path_collision_fails(self) -> None:
        target = "agent-factory-v1.2.3-macos-arm64.zip"
        self._write_bundle(portable_collision=target)
        with self.assertRaisesRegex(ReleaseVerificationError, "portable path collision"):
            verify_release(
                ReleaseSource(directory=self.release, base_url=None), "1.2.3", self.public_key
            )

    def test_zip_crc_is_checked_by_full_stream_read(self) -> None:
        target = "agent-factory-v1.2.3-windows-x86_64.zip"
        self._write_bundle(corrupt_crc=target)
        with self.assertRaisesRegex(ReleaseVerificationError, "CRC|invalid ZIP"):
            verify_release(
                ReleaseSource(directory=self.release, base_url=None), "1.2.3", self.public_key
            )

    def test_dot_segment_alias_is_rejected(self) -> None:
        target = "agent-factory-v1.2.3-macos-x86_64.zip"
        self._write_bundle(dot_alias=target)
        with self.assertRaisesRegex(ReleaseVerificationError, "unsafe path"):
            verify_release(
                ReleaseSource(directory=self.release, base_url=None), "1.2.3", self.public_key
            )

    def test_archive_member_count_limit_is_enforced(self) -> None:
        self._write_bundle()
        with mock.patch("tools.verify_release.MAX_ARCHIVE_MEMBERS", 1):
            with self.assertRaisesRegex(ReleaseVerificationError, "too many members"):
                verify_release(
                    ReleaseSource(directory=self.release, base_url=None),
                    "1.2.3",
                    self.public_key,
                )

    def test_archive_uncompressed_size_limit_is_enforced(self) -> None:
        self._write_bundle()
        with mock.patch("tools.verify_release.MAX_ARCHIVE_UNCOMPRESSED_BYTES", 5):
            with self.assertRaisesRegex(ReleaseVerificationError, "uncompressed size limit"):
                verify_release(
                    ReleaseSource(directory=self.release, base_url=None),
                    "1.2.3",
                    self.public_key,
                )


if __name__ == "__main__":
    unittest.main()
