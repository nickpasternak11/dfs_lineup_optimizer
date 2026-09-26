import subprocess

import pytest
import src.backup as backup


@pytest.fixture
def backup_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(backup, "BACKUP_RETENTION", 3)
    return tmp_path


def fake_pg_dump(calls, fail=False):
    def run(command, env, **kwargs):
        calls.append((command, env))
        target = next(arg for arg in command if arg.startswith("--file=")).split("=", 1)[1]
        with open(target, "w") as handle:
            handle.write("dump")
        if fail:
            raise subprocess.CalledProcessError(1, command, stderr="connection refused\n")

    return run


def test_writes_a_dump_with_the_database_credentials(backup_dir, monkeypatch):
    calls = []
    monkeypatch.setattr(backup.subprocess, "run", fake_pg_dump(calls))
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_HOST", "dfs-postgres")

    path = backup.run_backup()

    assert path.startswith(str(backup_dir))
    assert [p.name for p in backup_dir.iterdir()] == [path.rsplit("/", 1)[1]]
    command, env = calls[0]
    assert command[:2] == ["pg_dump", "--format=custom"]
    assert (env["PGPASSWORD"], env["PGHOST"]) == ("secret", "dfs-postgres")


def test_keeps_only_the_newest_dumps(backup_dir, monkeypatch):
    for day in range(1, 5):
        (backup_dir / f"dfs_2026090{day}T070000Z.dump").write_text("old")
    monkeypatch.setattr(backup.subprocess, "run", fake_pg_dump([]))

    newest = backup.run_backup()

    kept = sorted(p.name for p in backup_dir.iterdir())
    assert len(kept) == 3
    assert newest.rsplit("/", 1)[1] in kept
    assert "dfs_20260901T070000Z.dump" not in kept


def test_failed_dump_raises_and_leaves_old_backups_alone(backup_dir, monkeypatch):
    old = [backup_dir / f"dfs_2026090{day}T070000Z.dump" for day in range(1, 5)]
    for path in old:
        path.write_text("old")
    monkeypatch.setattr(backup.subprocess, "run", fake_pg_dump([], fail=True))

    with pytest.raises(RuntimeError, match="connection refused"):
        backup.run_backup()

    # Nothing pruned, and no half-written file left behind.
    assert sorted(backup_dir.iterdir()) == sorted(old)
