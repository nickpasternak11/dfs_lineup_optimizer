"""Nightly pg_dump of the dfs database to a host directory.

Runs pg_dump in a throwaway container from the same image as dfs-postgres, so
the client always matches the server version. Dumps land in BACKUP_DIR on the
host -- outside the dfs_postgres_data volume, so `docker compose down -v`
can't take the backups with it.

Run on demand with `make backup` (python -m src.backup).
"""

import os

import docker
from src.configs import log

BACKUP_IMAGE = "postgres:16-alpine"
BACKUP_DIR = os.getenv("BACKUP_DIR", "/dfs_backups")
BACKUP_RETENTION = int(os.getenv("BACKUP_RETENTION", "14"))
NETWORK_NAME = "dfs_optimizer_network"

# Written as .partial and renamed on success, so a failed dump never counts
# toward retention; `set -e` means pruning only runs after a good dump.
BACKUP_SCRIPT = (
    "set -e; "
    'file="/backups/dfs_$(date -u +%Y%m%dT%H%M%SZ).dump"; '
    'pg_dump --format=custom --file="$file.partial"; '
    'mv "$file.partial" "$file"; '
    'ls -1t /backups/dfs_*.dump | tail -n +"$((RETENTION + 1))" | xargs -r rm --; '
    'echo "Wrote $file ($(du -h "$file" | cut -f1))"'
)


def run_backup(client: docker.DockerClient | None = None) -> None:
    client = client or docker.from_env()
    environment = {
        "PGHOST": os.getenv("POSTGRES_HOST", "dfs-postgres"),
        "PGPORT": os.getenv("POSTGRES_PORT", "5432"),
        "PGDATABASE": os.getenv("POSTGRES_DB", "dfs"),
        "PGUSER": os.getenv("POSTGRES_USER", "dfs"),
        "PGPASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "RETENTION": str(BACKUP_RETENTION),
    }

    log.info("Backing up database to %s (keeping %s)..", BACKUP_DIR, BACKUP_RETENTION)
    # Non-detached run raises ContainerError on a non-zero exit.
    output = client.containers.run(
        BACKUP_IMAGE,
        command=["sh", "-c", BACKUP_SCRIPT],
        environment=environment,
        volumes={BACKUP_DIR: {"bind": "/backups", "mode": "rw"}},
        network=NETWORK_NAME,
        labels={"logging": "promtail"},
        remove=True,
    )
    log.info(output.decode().strip())


if __name__ == "__main__":
    run_backup()
