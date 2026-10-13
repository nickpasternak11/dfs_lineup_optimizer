"""Keep player names in FantasyPros' rankings spelling.

FantasyPros' weekly rankings carry the canonical name ("A.J. Brown",
"Patrick Mahomes II", "KC Concepcion Jr."), but other sources drop
punctuation or suffixes: the legacy CSVs ("AJ Brown", "Patrick Mahomes") and
sometimes the DraftKings salary page ("KC Concepcion"). weekly_player_pool
joins salaries to projections on the exact name, so a mismatch silently drops
the player from the pool.

- reconcile_week_names() renames one week's salary rows to that week's
  projection spellings; both scrapers call it after writing.
- normalize_names() is the one-time cleanup of history, run with
  `make normalize-names` (`ARGS=--dry-run` to preview; see normalize.py).
  Safe to re-run.

Names match when they agree on position and on their letters, ignoring case,
punctuation and a trailing Jr./Sr./II-V.
"""

import re
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import text

_SUFFIX = re.compile(r"\s+(jr\.?|sr\.?|ii|iii|iv|v)$", re.IGNORECASE)

TABLES = ("player_salaries", "player_projections")


def name_key(name: str) -> str:
    return re.sub(r"[^a-z]", "", _SUFFIX.sub("", name.strip()).lower())


@dataclass(frozen=True)
class NameUsage:
    """One spelling of one player, as found in the tables."""

    name: str
    position: str
    first_year: int
    last_year: int
    has_fp_id: bool = False


@dataclass(frozen=True)
class Rename:
    position: str
    old: str
    new: str
    # Rows from earlier seasons keep the old spelling: a father and son can
    # share a name up to the suffix (Frank Gore, Frank Gore Jr.), and the
    # son's spelling can't be right for seasons before it ever appeared.
    from_year: int


def canonical(variants: list[NameUsage]) -> NameUsage | None:
    """The FantasyPros spelling among one player's spellings.

    A spelling scraped with a FantasyPros id came from the rankings, so it is
    canonical outright; two such spellings are ambiguous and left alone.
    Otherwise the longest wins, since every other source only ever drops
    characters (punctuation, suffixes) from FantasyPros' spelling.
    """
    with_id = [v for v in variants if v.has_fp_id]
    if len(with_id) > 1:
        return None
    if with_id:
        return with_id[0]
    return max(variants, key=lambda v: (len(v.name), v.last_year, v.name))


def plan_renames(usages: list[NameUsage]) -> list[Rename]:
    merged: dict[tuple[str, str], NameUsage] = {}
    for usage in usages:
        known = merged.get((usage.name, usage.position))
        merged[(usage.name, usage.position)] = (
            usage
            if known is None
            else NameUsage(
                usage.name,
                usage.position,
                min(known.first_year, usage.first_year),
                max(known.last_year, usage.last_year),
                known.has_fp_id or usage.has_fp_id,
            )
        )

    players: dict[tuple[str, str], list[NameUsage]] = defaultdict(list)
    for usage in merged.values():
        players[(name_key(usage.name), usage.position)].append(usage)

    renames = []
    for variants in players.values():
        if len(variants) < 2 or (target := canonical(variants)) is None:
            continue
        renames.extend(
            Rename(v.position, v.name, target.name, target.first_year)
            for v in variants
            if v.name != target.name
        )
    return sorted(renames, key=lambda r: (r.position, r.new, r.old))


def week_renames(
    salary_names: set[tuple[str, str]], projection_names: set[tuple[str, str]]
) -> dict[tuple[str, str], str]:
    """{(salary name, position): projection name} for one week.

    Only when exactly one projection name matches, and it isn't already a
    salary name that week (which would collide on the primary key).
    """
    by_key: dict[tuple[str, str], list[str]] = defaultdict(list)
    for name, position in projection_names:
        by_key[(name_key(name), position)].append(name)

    renames = {}
    for name, position in salary_names - projection_names:
        matches = by_key.get((name_key(name), position), [])
        if len(matches) == 1 and (matches[0], position) not in salary_names:
            renames[(name, position)] = matches[0]
    return renames


WEEK_NAMES = {
    table: text(f"SELECT DISTINCT player, position FROM {table} WHERE year = :year AND week = :week")
    for table in TABLES
}
RENAME_WEEK_SALARY = text(
    "UPDATE player_salaries SET player = :new "
    "WHERE year = :year AND week = :week AND player = :old AND position = :position"
)


def reconcile_week_names(session, year: int, week: int) -> int:
    """Rename one week's salary rows to that week's projection spellings."""
    params = {"year": int(year), "week": int(week)}
    salaries, projections = (
        {tuple(row) for row in session.execute(WEEK_NAMES[table], params)} for table in TABLES
    )
    renames = week_renames(salaries, projections)
    for (old, position), new in renames.items():
        session.execute(RENAME_WEEK_SALARY, {**params, "old": old, "new": new, "position": position})
    return len(renames)


USAGES = text(
    """
    SELECT player, position, min(year), max(year), bool_or(fp_player_id IS NOT NULL)
    FROM player_projections GROUP BY player, position
    UNION ALL
    SELECT player, position, min(year), max(year), false
    FROM player_salaries GROUP BY player, position
    """
)


def _rename_statement(table: str, count_only: bool):
    # Rows whose week already has the new spelling stay put: renaming them
    # would collide on the primary key.
    where = f"""
        WHERE t.player = :old AND t.position = :position AND t.year >= :from_year
          AND NOT EXISTS (
              SELECT 1 FROM {table} AS o
              WHERE o.year = t.year AND o.week = t.week AND o.player = :new)
    """
    if count_only:
        return text(f"SELECT count(*) FROM {table} AS t {where}")
    return text(f"UPDATE {table} AS t SET player = :new {where}")


def normalize_names(session, dry_run: bool = False) -> list[tuple[Rename, dict[str, int]]]:
    """Rename every spelling variant to FantasyPros' spelling; returns what
    was (or, with dry_run, would be) renamed per table."""
    usages = [NameUsage(*row) for row in session.execute(USAGES)]
    report = []
    for rename in plan_renames(usages):
        params = {
            "old": rename.old,
            "new": rename.new,
            "position": rename.position,
            "from_year": rename.from_year,
        }
        counts = {}
        for table in TABLES:
            result = session.execute(_rename_statement(table, count_only=dry_run), params)
            counts[table] = result.scalar_one() if dry_run else result.rowcount
        report.append((rename, counts))
    return report
