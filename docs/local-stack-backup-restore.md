# Local stack backup and restore

This procedure covers the **development Compose stack** in `compose.full.yml`. It snapshots the PostgreSQL and Chroma named volumes after all project containers have stopped. The restore command creates volumes for a **new** Compose project and refuses an existing target. It does not back up `backend/.env`, secrets, external provider data, or a production deployment.

## Persistence path and existing data

The current `chromadb/chroma:latest` image reports `persist_path: "/data"`. Both repository Compose files now mount `chroma_data:/data`. The former `/chroma/chroma` mount could leave writes in the container's writable layer, outside the named volume. Before recreating any **existing** Chroma container that used the former mount, inspect its logs and preserve its actual `/data` contents. Do not assume an old `chroma_data` volume contains those records. A removed container's writable layer is not recoverable from that empty volume.

The image tag `latest` and default development credentials in these Compose files are unsuitable as a production backup policy. Use a fixed image version, separate credentials, storage retention, and access controls in a target deployment.

## Offline backup

Use an explicit project name. Stop writers before taking a volume snapshot; the script refuses any running container in that project. Store the snapshot directory on storage with restricted access because PostgreSQL contains user data and encrypted application secrets.

```bash
docker compose -f compose.full.yml -p myproject stop
backend/.venv/bin/python scripts/local_stack_snapshot.py backup \
  --project myproject --snapshot /secure/path/myproject-2026-09-30
```

The directory contains `postgres.tar`, `chroma.tar`, and `manifest.json` with SHA-256 hashes. The tool rejects empty archives, missing volumes, and an existing output directory. Keep the application encryption key and JWT configuration separately; a database restore cannot decrypt stored provider settings without the original encryption key.

## Restore drill in a new project

Stop the source project or otherwise free the Compose host ports before starting the restored project. The target name must differ from the source and must have no containers or volumes. The command checks archive hashes before creating target volumes.

```bash
backend/.venv/bin/python scripts/local_stack_snapshot.py restore \
  --project myproject_restore --snapshot /secure/path/myproject-2026-09-30
docker compose -f compose.full.yml -p myproject_restore up -d postgres chroma
docker compose -f compose.full.yml -p myproject_restore exec -T postgres \
  psql -U insight -d insightagent -At -c 'SELECT count(*) FROM sessions;'
```

Use `backend/.venv/bin/python` with `chromadb.HttpClient(host="127.0.0.1", port=8001)` to list expected Memory/RAG collections and read a known document ID. For a real application dataset, also start the backend with the matching secrets and verify login, a known session, task Trace, and knowledge base query. Record the backup timestamp, restoration start/end, observed data age (RPO), elapsed recovery time (RTO), owner, and any failed check in the environment's runbook. Do not mark `INSIGHT_AGENT_BACKUP_LAST_RESTORE_DRILL_AT` from a fixture-only test.

Only after checking that `myproject_restore` is the disposable drill project, remove its resources with `docker compose -f compose.full.yml -p myproject_restore down -v`. The backup tool itself never deletes an existing project volume.

## Local fixture evidence

On 2026-09-30, an isolated `iasnapcheck2` fixture wrote one PostgreSQL row and one Chroma vector. After stopping both services, the tool snapshotted their volumes and restored into `iasnaprestore2`. Both values were read back. The first run exposed the old Chroma mount error: its archive contained only `./` while the server logged `Saving data to: /data`. This is a development-stack recovery check, not a target-environment restore or an RPO/RTO acceptance result.
