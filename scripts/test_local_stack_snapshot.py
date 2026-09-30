#!/usr/bin/env python3
"""Safety checks for the offline local stack snapshot workflow."""

import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("local_stack_snapshot.py")
SPEC = importlib.util.spec_from_file_location("local_stack_snapshot", SCRIPT)
snapshot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot)


def write_archive(_volume, directory, filename):
    with tarfile.open(directory / filename, "w") as archive:
        content = b"probe"
        entry = tarfile.TarInfo("probe.txt")
        entry.size = len(content)
        archive.addfile(entry, io.BytesIO(content))


class LocalStackSnapshotTests(unittest.TestCase):
    def test_backup_refuses_running_services_before_reading_volumes(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(snapshot, "compose", return_value="container-id") as compose:
                with patch.object(snapshot, "volume_exists") as volume_exists:
                    with self.assertRaisesRegex(RuntimeError, "running Compose containers"):
                        snapshot.backup("source", Path(directory) / "snapshot")
                volume_exists.assert_not_called()
                compose.assert_called_once_with("source", "ps", "--status", "running", "-q", capture=True)

    def test_restore_refuses_same_project_and_corrupt_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "snapshot"
            with patch.object(snapshot, "compose", return_value=""):
                with patch.object(snapshot, "volume_exists", return_value=True):
                    with patch.object(snapshot, "archive_volume", side_effect=write_archive):
                        snapshot.backup("source", target)
            with self.assertRaisesRegex(RuntimeError, "different, isolated"):
                snapshot.restore("source", target)
            (target / "chroma.tar").write_bytes(b"corrupt")
            with self.assertRaisesRegex(RuntimeError, "integrity check failed"):
                snapshot.restore("newproject", target)

    def test_restore_refuses_existing_target_volume(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "snapshot"
            with patch.object(snapshot, "compose", return_value=""):
                with patch.object(snapshot, "volume_exists", return_value=True):
                    with patch.object(snapshot, "archive_volume", side_effect=write_archive):
                        snapshot.backup("source", target)
                with patch.object(snapshot, "volume_exists", return_value=True):
                    with self.assertRaisesRegex(RuntimeError, "target volume already exists"):
                        snapshot.restore("newproject", target)

    def test_backup_rejects_empty_chroma_volume(self):
        def write_empty_chroma(volume, directory, filename):
            if filename == "chroma.tar":
                with tarfile.open(directory / filename, "w"):
                    pass
            else:
                write_archive(volume, directory, filename)

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "snapshot"
            with patch.object(snapshot, "compose", return_value=""):
                with patch.object(snapshot, "volume_exists", return_value=True):
                    with patch.object(snapshot, "archive_volume", side_effect=write_empty_chroma):
                        with self.assertRaisesRegex(RuntimeError, "empty volume archive: chroma.tar"):
                            snapshot.backup("source", target)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
