from __future__ import annotations

import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tools import publish_release as publisher


REVISION = "a" * 40


def completed(
    command: list[str],
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


class PublishReleaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="agent-factory-publisher-test-")
        self.staging = Path(self.temporary.name) / "staging"
        self.staging.mkdir()
        for name in publisher._artifact_names("0.1.2"):
            (self.staging / name).write_bytes(f"content:{name}".encode())

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def plan(self) -> publisher.ReleasePlan:
        return publisher.build_plan(
            version="0.1.2",
            tag="v0.1.2",
            staging=self.staging,
        )

    def prepared(self) -> publisher.PreparedRelease:
        plan = self.plan()
        return publisher.PreparedRelease(
            plan=plan,
            client_revision=REVISION,
            asset_digests=publisher._asset_digests(plan.assets),
        )

    def test_accepts_exact_v012_tag_with_prerelease_metadata(self) -> None:
        plan = self.plan()

        self.assertEqual(plan.version, "0.1.2")
        self.assertEqual(plan.tag, "v0.1.2")
        self.assertEqual(len(plan.assets), 7)
        self.assertEqual(
            {path.name for path in plan.assets}, set(publisher._artifact_names("0.1.2"))
        )

    def test_rejects_decorated_or_mismatched_tags_and_extra_staging_files(self) -> None:
        for tag in ("v0.1.2-beta.1", "v0.1.3", "0.1.2"):
            with self.subTest(tag=tag), self.assertRaises(publisher.PublishError):
                publisher.build_plan(version="0.1.2", tag=tag, staging=self.staging)

        (self.staging / "private-signing-key.pem").write_text("must not be published")
        with self.assertRaisesRegex(publisher.PublishError, "unexpected files"):
            self.plan()

    def test_checkout_requires_clean_main_and_matching_github_origin(self) -> None:
        plan = self.plan()

        def output(command: list[str]) -> str:
            values = {
                ("git", "branch", "--show-current"): "main",
                ("git", "status", "--porcelain", "--untracked-files=all"): "",
                ("git", "remote", "get-url", "origin"):
                    "https://github.com/RoKenshi/agent-factory-client.git",
                ("git", "rev-parse", "HEAD"): REVISION,
            }
            return values[tuple(command)]

        with patch.object(publisher, "_output", side_effect=output):
            self.assertEqual(publisher._assert_local_checkout(plan), REVISION)

        with patch.object(
            publisher,
            "_output",
            side_effect=lambda command: (
                "feature" if command == ["git", "branch", "--show-current"] else ""
            ),
        ):
            with self.assertRaisesRegex(publisher.PublishError, "branch main"):
                publisher._assert_local_checkout(plan)

    def test_prepare_fetches_origin_checks_gh_and_runs_release_check(self) -> None:
        plan = self.plan()
        commands: list[list[str]] = []

        def run(
            command: list[str],
            *,
            check: bool = True,
            capture_output: bool = True,
        ) -> subprocess.CompletedProcess[str]:
            del check, capture_output
            commands.append(command)
            return completed(command)

        outputs = iter(("RoKenshi/agent-factory-client",))

        with (
            patch.object(publisher, "_require_tools"),
            patch.object(
                publisher,
                "_assert_local_checkout",
                side_effect=(REVISION, REVISION, REVISION),
            ),
            patch.object(
                publisher,
                "_output",
                side_effect=lambda command: (
                    REVISION
                    if command == ["git", "rev-parse", "origin/main"]
                    else next(outputs)
                ),
            ),
            patch.object(publisher, "_ensure_release_absent"),
            patch.object(publisher, "run_command", side_effect=run),
        ):
            prepared = publisher.prepare_release(plan)

        self.assertEqual(prepared.client_revision, REVISION)
        self.assertIn(["git", "fetch", "--prune", "--tags", "origin"], commands)
        self.assertIn(["gh", "auth", "status", "--hostname", "github.com"], commands)
        self.assertIn(
            [
                "sh",
                str(publisher.ROOT / "tools/release-check.sh"),
                "0.1.2",
                str(plan.staging),
            ],
            commands,
        )

    def test_prepare_refuses_head_that_differs_from_fetched_origin_main(self) -> None:
        plan = self.plan()
        commands: list[list[str]] = []

        with (
            patch.object(publisher, "_require_tools"),
            patch.object(
                publisher, "_assert_local_checkout", side_effect=(REVISION, REVISION)
            ),
            patch.object(publisher, "_output", return_value="b" * 40),
            patch.object(
                publisher,
                "run_command",
                side_effect=lambda command, **_: (
                    commands.append(command) or completed(command)
                ),
            ),
        ):
            with self.assertRaisesRegex(publisher.PublishError, "freshly fetched origin/main"):
                publisher.prepare_release(plan)

        self.assertIn(["git", "fetch", "--prune", "--tags", "origin"], commands)
        self.assertFalse(any(command[0] == "sh" for command in commands))

    def test_existing_release_is_never_replaced(self) -> None:
        plan = self.plan()
        responses = iter(
            (
                completed(["git", "show-ref"], returncode=1),
                completed(["gh", "release", "view"]),
            )
        )
        with patch.object(publisher, "run_command", side_effect=lambda *_, **__: next(responses)):
            with self.assertRaisesRegex(publisher.PublishError, "will not be replaced"):
                publisher._ensure_release_absent(plan)

    def test_default_mode_is_dry_run_and_never_calls_publisher(self) -> None:
        prepared = self.prepared()
        output = io.StringIO()
        arguments = [
            "--version",
            "0.1.2",
            "--tag",
            "v0.1.2",
            "--staging",
            str(self.staging),
        ]

        with (
            patch.object(publisher, "prepare_release", return_value=prepared),
            patch.object(publisher, "publish_release") as publish,
            redirect_stdout(output),
        ):
            result = publisher.main(arguments)

        self.assertEqual(result, 0)
        publish.assert_not_called()
        self.assertIn("mode: dry-run", output.getvalue())
        self.assertIn("latest=false", output.getvalue())

    def test_execute_requires_exact_revision_bound_confirmation(self) -> None:
        prepared = self.prepared()
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(publisher.PublishError, "refusing publication"):
                publisher.publish_release(prepared)

    def test_execute_publishes_exactly_seven_assets_as_non_latest_prerelease(self) -> None:
        prepared = self.prepared()
        commands: list[list[str]] = []

        def run(
            command: list[str],
            *,
            check: bool = True,
            capture_output: bool = True,
        ) -> subprocess.CompletedProcess[str]:
            del check, capture_output
            commands.append(command)
            return completed(command)

        payload = {
            "tagName": prepared.plan.tag,
            "isDraft": False,
            "isPrerelease": True,
            "targetCommitish": REVISION,
            "assets": [{"name": path.name} for path in prepared.plan.assets],
            "url": "https://github.com/RoKenshi/agent-factory-client/releases/tag/"
            + prepared.plan.tag,
        }
        with (
            patch.dict(
                "os.environ", {publisher.CONFIRMATION_ENV: prepared.confirmation}, clear=True
            ),
            patch.object(publisher, "_assert_local_checkout", return_value=REVISION),
            patch.object(publisher, "_output", return_value=REVISION),
            patch.object(publisher, "_ensure_release_absent"),
            patch.object(publisher, "run_command", side_effect=run),
            patch.object(publisher, "_read_release", return_value=payload),
            patch.object(publisher, "_latest_tag", return_value="v0.1.1"),
        ):
            url = publisher.publish_release(prepared)

        create = next(command for command in commands if command[:3] == ["gh", "release", "create"])
        uploaded = create[4 : create.index("--repo")]
        self.assertEqual(len(uploaded), 7)
        self.assertEqual(
            {Path(path).name for path in uploaded},
            set(publisher._artifact_names("0.1.2")),
        )
        self.assertIn("--prerelease", create)
        self.assertIn("--latest=false", create)
        self.assertNotIn("--latest", create)
        self.assertEqual(create[create.index("--target") + 1], REVISION)
        self.assertTrue(url.endswith(prepared.plan.tag))

    def test_changed_asset_is_rejected_before_gh_create(self) -> None:
        prepared = self.prepared()
        prepared.plan.assets[0].write_bytes(b"changed")
        commands: list[list[str]] = []

        with (
            patch.dict(
                "os.environ", {publisher.CONFIRMATION_ENV: prepared.confirmation}, clear=True
            ),
            patch.object(publisher, "_assert_local_checkout", return_value=REVISION),
            patch.object(publisher, "_output", return_value=REVISION),
            patch.object(publisher, "_ensure_release_absent"),
            patch.object(
                publisher,
                "run_command",
                side_effect=lambda command, **_: (
                    commands.append(command) or completed(command)
                ),
            ),
        ):
            with self.assertRaisesRegex(publisher.PublishError, "changed after verification"):
                publisher.publish_release(prepared)

        self.assertFalse(
            any(command[:3] == ["gh", "release", "create"] for command in commands)
        )

    def test_non_prerelease_postcondition_is_quarantined(self) -> None:
        prepared = self.prepared()
        payload = {
            "tagName": prepared.plan.tag,
            "isDraft": False,
            "isPrerelease": False,
            "targetCommitish": REVISION,
            "assets": [{"name": path.name} for path in prepared.plan.assets],
        }
        commands: list[list[str]] = []

        with (
            patch.object(publisher, "_read_release", return_value=payload),
            patch.object(publisher, "_latest_tag", return_value=None),
            patch.object(
                publisher,
                "run_command",
                side_effect=lambda command, **_: (
                    commands.append(command) or completed(command)
                ),
            ),
        ):
            with self.assertRaisesRegex(publisher.PublishError, "quarantined"):
                publisher._verify_published_release(prepared)

        edit = next(command for command in commands if command[:3] == ["gh", "release", "edit"])
        self.assertIn("--draft=true", edit)
        self.assertIn("--prerelease=true", edit)
        self.assertIn("--latest=false", edit)


if __name__ == "__main__":
    unittest.main()
