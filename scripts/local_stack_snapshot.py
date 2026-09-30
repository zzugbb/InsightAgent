#!/usr/bin/env python3
"""Offline PostgreSQL and Chroma volume snapshots for the local Compose stack."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "compose.full.yml"
HELPER_IMAGE = "postgres:16-alpine"
VOLUMES = {"postgres": "pg_data", "chroma": "chroma_data"}
PROJECT_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]*\Z")


def run(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        args,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def compose(project: str, *args: str, capture: bool = False) -> str:
    return run("docker", "compose", "-f", str(COMPOSE), "-p", project, *args, capture=capture)


def volume_name(project: str, logical_name: str) -> str:
    return f"{project}_{logical_name}"


def volume_exists(name: str) -> bool:
    result = subprocess.run(
        ("docker", "volume", "inspect", name),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def assert_archive_has_files(path: Path) -> None:
    with tarfile.open(path) as archive:
        if not any(member.isfile() for member in archive):
            raise RuntimeError(f"empty volume archive: {path.name}; check the container persistence mount")


def assert_no_containers(project: str, *, include_stopped: bool) -> None:
    args = ("ps", "-a", "-q") if include_stopped else ("ps", "--status", "running", "-q")
    if compose(project, *args, capture=True):
        state = "any" if include_stopped else "running"
        raise RuntimeError(f"{project}: {state} Compose containers exist; stop/remove them first")


def archive_volume(volume: str, directory: Path, filename: str) -> None:
    run(
        "docker", "run", "--rm", "--pull", "never", "--network", "none",
        "-v", f"{volume}:/source:ro", "-v", f"{directory}:/out",
        HELPER_IMAGE, "sh", "-c", f"cd /source && tar -cf /out/{filename} .",
    )


def extract_volume(volume: str, directory: Path, filename: str) -> None:
    run(
        "docker", "run", "--rm", "--pull", "never", "--network", "none",
        "-v", f"{volume}:/target", "-v", f"{directory}:/in:ro",
        HELPER_IMAGE, "sh", "-c", f"tar -xf /in/{filename} -C /target",
    )


def backup(project: str, output: Path) -> None:
    assert_no_containers(project, include_stopped=False)
    for logical_name in VOLUMES.values():
        if not volume_exists(volume_name(project, logical_name)):
            raise RuntimeError(f"missing volume: {volume_name(project, logical_name)}")
    output = output.resolve()
    if output.exists():
        raise RuntimeError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="stack-snapshot-", dir=output.parent))
    try:
        archives = {}
        for key, logical_name in VOLUMES.items():
            filename = f"{key}.tar"
            archive_volume(volume_name(project, logical_name), staging, filename)
            assert_archive_has_files(staging / filename)
            archives[key] = {"file": filename, "sha256": digest(staging / filename)}
        manifest = {
            "schema_version": 1,
            "source_project": project,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "archives": archives,
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    print(f"snapshot ready: {output}")


def validated_archives(snapshot: Path) -> tuple[str, dict[str, str]]:
    manifest = json.loads((snapshot / "manifest.json").read_text())
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise RuntimeError("unsupported snapshot manifest")
    source_project = manifest.get("source_project")
    if not isinstance(source_project, str) or not PROJECT_PATTERN.fullmatch(source_project):
        raise RuntimeError("unsupported snapshot manifest")
    archives = {}
    for key in VOLUMES:
        entry = manifest.get("archives", {}).get(key, {})
        filename = f"{key}.tar"
        path = snapshot / filename
        if entry.get("file") != filename or not path.is_file() or digest(path) != entry.get("sha256"):
            raise RuntimeError(f"snapshot integrity check failed: {filename}")
        assert_archive_has_files(path)
        archives[key] = filename
    return source_project, archives


def restore(project: str, snapshot: Path) -> None:
    snapshot = snapshot.resolve()
    source_project, archives = validated_archives(snapshot)
    if project == source_project:
        raise RuntimeError("restore requires a different, isolated Compose project")
    assert_no_containers(project, include_stopped=True)
    names = {key: volume_name(project, logical_name) for key, logical_name in VOLUMES.items()}
    for name in names.values():
        if volume_exists(name):
            raise RuntimeError(f"target volume already exists: {name}")
    created = []
    try:
        for key, logical_name in VOLUMES.items():
            name = names[key]
            run(
                "docker", "volume", "create",
                "--label", f"com.docker.compose.project={project}",
                "--label", f"com.docker.compose.volume={logical_name}", name,
            )
            created.append(name)
            extract_volume(name, snapshot, archives[key])
    except Exception:
        for name in reversed(created):
            subprocess.run(("docker", "volume", "rm", name), check=False, stdout=subprocess.DEVNULL)
        raise
    print(f"restored into new project volumes: {project}; start services and verify data before use")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("backup", "restore"):
        command = subparsers.add_parser(action)
        command.add_argument("--project", required=True, help="explicit Compose project name")
        command.add_argument("--snapshot", required=True, type=Path, help="snapshot directory")
    args = parser.parse_args()
    if not PROJECT_PATTERN.fullmatch(args.project):
        parser.error("project must use lowercase letters, digits, hyphens or underscores")
    try:
        if args.action == "backup":
            backup(args.project, args.snapshot)
        else:
            restore(args.project, args.snapshot)
    except (OSError, ValueError, KeyError, tarfile.TarError, subprocess.CalledProcessError, RuntimeError) as exc:
        parser.exit(1, f"snapshot failed: {exc}\n")


if __name__ == "__main__":
    main()
