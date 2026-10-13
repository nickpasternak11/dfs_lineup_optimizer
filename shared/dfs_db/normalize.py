"""`python -m dfs_db.normalize [--dry-run]`: rename stored players to
FantasyPros' spelling (see dfs_db.names). Run via `make normalize-names`."""

import sys

from dfs_db.links import refresh_player_links
from dfs_db.names import normalize_names
from dfs_db.session import session_scope


def main(argv: list[str]) -> None:
    dry_run = "--dry-run" in argv
    with session_scope() as session:
        report = normalize_names(session, dry_run=dry_run)
        if not dry_run:
            # The links are keyed by pool name.
            refresh_player_links(session)

    total = 0
    for rename, counts in report:
        total += sum(counts.values())
        detail = ", ".join(f"{n} in {table}" for table, n in counts.items() if n)
        print(
            f"{rename.position:3} {rename.old!r} -> {rename.new!r} "
            f"(from {rename.from_year}): {detail or 'nothing'}"
        )
    verb = "Would rename" if dry_run else "Renamed"
    print(f"{verb} {total} rows across {len(report)} spellings.")


if __name__ == "__main__":
    main(sys.argv[1:])
