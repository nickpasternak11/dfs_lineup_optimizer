"""Nightly pg_dump of the dfs database to a host directory.

BACKUP_DIR is a host directory mounted at /backups (see docker-compose.run.yml),
outside the dfs_postgres_data volume, so `docker compose down -v` can't take
the backups with it.

Run on demand with `make backup` (python -m src.backup).
"""

import glob
import os
import subprocess
from datetime import datetime, timezone

from src.configs import log

BACKUP_DIR = "/backups"
BACKUP_RETENTION = int(os.getenv("BACKUP_RETENTION", "14"))


def run_backup() -> str:
    """Dump the database and prune old dumps; returns the new file's path.

    Raises on failure, leaving earlier backups untouched.
    """
    env = {
        **os.environ,
        "PGHOST": os.getenv("POSTGRES_HOST", "dfs-postgres"),
        "PGPORT": os.getenv("POSTGRES_PORT", "5432"),
        "PGDATABASE": os.getenv("POSTGRES_DB", "dfs"),
        "PGUSER": os.getenv("POSTGRES_USER", "dfs"),
        "PGPASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(BACKUP_DIR, f"dfs_{stamp}.dump")
    # Written under another name and renamed on success, so a failed dump
    # never counts toward retention or pushes out a good one.
    partial = f"{path}.partial"

    log.info("Backing up database to %s (keeping %s)..", BACKUP_DIR, BACKUP_RETENTION)
    try:
        subprocess.run(
            ["pg_dump", "--format=custom", f"--file={partial}"],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        if os.path.exists(partial):
            os.remove(partial)
        raise RuntimeError(f"pg_dump failed: {error.stderr.strip()}") from error
    os.replace(partial, path)

    # Timestamped names sort chronologically.
    dumps = sorted(glob.glob(os.path.join(BACKUP_DIR, "dfs_*.dump")), reverse=True)
    for old in dumps[BACKUP_RETENTION:]:
        os.remove(old)
        log.info("Removed old backup %s", os.path.basename(old))

    size_kb = os.path.getsize(path) / 1024
    log.info("Wrote %s (%.0fK)", path, size_kb)
    return path


if __name__ == "__main__":
    run_backup()
