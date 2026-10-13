import pytest
from dfs_db.names import (
    NameUsage,
    Rename,
    name_key,
    normalize_names,
    plan_renames,
    reconcile_week_names,
    week_renames,
)


@pytest.mark.parametrize(
    "a, b",
    [
        ("A.J. Brown", "AJ Brown"),
        ("Ja'Marr Chase", "JaMarr Chase"),
        ("Amon-Ra St. Brown", "Amon-Ra St Brown"),
        ("Patrick Mahomes II", "Patrick Mahomes"),
        ("Kenneth Walker III", "Kenneth Walker"),
        ("Travis Etienne Jr.", "Travis Etienne"),
        ("Aaron Jones Sr.", "aaron jones"),
    ],
)
def test_spellings_of_one_name_share_a_key(a, b):
    assert name_key(a) == name_key(b)


def test_different_names_keep_different_keys():
    assert name_key("Mike Williams") != name_key("Mike Thomas")
    # Only a trailing suffix is dropped.
    assert name_key("Justin Jefferson") != name_key("Justin Jeff")


def usage(name, position="WR", first=2024, last=2026, has_fp_id=False):
    return NameUsage(name, position, first, last, has_fp_id)


def test_the_spelling_scraped_with_an_id_wins():
    renames = plan_renames([usage("AJ Brown"), usage("A.J. Brown", first=2018, has_fp_id=True)])
    assert renames == [Rename("WR", "AJ Brown", "A.J. Brown", 2018)]


def test_an_id_beats_length():
    renames = plan_renames([usage("Kenneth Walker", "RB", has_fp_id=True), usage("Kenneth Walker III", "RB")])
    assert renames == [Rename("RB", "Kenneth Walker III", "Kenneth Walker", 2024)]


def test_without_an_id_the_longest_spelling_wins():
    renames = plan_renames([usage("Patrick Mahomes", "QB"), usage("Patrick Mahomes II", "QB", first=2018)])
    assert renames == [Rename("QB", "Patrick Mahomes", "Patrick Mahomes II", 2018)]


def test_two_spellings_with_ids_are_left_alone():
    assert plan_renames([usage("Velus Jones", has_fp_id=True), usage("Velus Jones Jr.", has_fp_id=True)]) == []


def test_a_fathers_seasons_keep_his_name():
    # Frank Gore played through 2020; Frank Gore Jr. appears from 2024.
    renames = plan_renames(
        [usage("Frank Gore", "RB", 2018, 2024), usage("Frank Gore Jr.", "RB", 2024, 2026, has_fp_id=True)]
    )
    assert renames == [Rename("RB", "Frank Gore", "Frank Gore Jr.", 2024)]


def test_positions_are_never_merged():
    assert plan_renames([usage("Taysom Hill", "QB"), usage("Taysom Hill Jr.", "TE")]) == []


def test_one_name_in_both_tables_counts_once():
    # Salaries and projections each report "AJ Brown"; the earliest season of
    # the canonical spelling comes from either table.
    renames = plan_renames(
        [usage("AJ Brown"), usage("AJ Brown"), usage("A.J. Brown", first=2020), usage("A.J. Brown", first=2018)]
    )
    assert renames == [Rename("WR", "AJ Brown", "A.J. Brown", 2018)]


def test_a_week_adopts_the_rankings_spelling():
    salaries = {("KC Concepcion", "WR"), ("Josh Allen", "QB")}
    projections = {("KC Concepcion Jr.", "WR"), ("Josh Allen", "QB")}
    assert week_renames(salaries, projections) == {("KC Concepcion", "WR"): "KC Concepcion Jr."}


def test_a_week_never_renames_into_an_existing_row():
    salaries = {("KC Concepcion", "WR"), ("KC Concepcion Jr.", "WR")}
    assert week_renames(salaries, {("KC Concepcion Jr.", "WR")}) == {}


def test_a_week_skips_ambiguous_matches_and_other_positions():
    salaries = {("Mike Williams", "WR"), ("Taysom Hill", "TE")}
    projections = {("Mike Williams Jr.", "WR"), ("Mike Williams Sr.", "WR"), ("Taysom Hill Jr.", "QB")}
    assert week_renames(salaries, projections) == {}


class FakeSession:
    """Answers name queries from `tables`; records every statement."""

    def __init__(self, tables: dict[str, list[tuple]], usages: list[tuple] = ()):
        self.tables = tables
        self.usages = list(usages)
        self.executed = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.executed.append((sql, params))
        if sql.startswith("SELECT DISTINCT"):
            table = "player_salaries" if "player_salaries" in sql else "player_projections"
            return iter(self.tables[table])
        if "UNION ALL" in sql:
            return iter(self.usages)
        return _Result()


class _Result:
    rowcount = 2

    def scalar_one(self):
        return 3


def test_reconcile_week_renames_that_weeks_salary_rows():
    session = FakeSession(
        {
            "player_salaries": [("KC Concepcion", "WR"), ("Josh Allen", "QB")],
            "player_projections": [("KC Concepcion Jr.", "WR"), ("Josh Allen", "QB")],
        }
    )
    assert reconcile_week_names(session, 2026, 1) == 1
    sql, params = session.executed[-1]
    assert sql.startswith("UPDATE player_salaries")
    assert params == {"year": 2026, "week": 1, "old": "KC Concepcion", "new": "KC Concepcion Jr.", "position": "WR"}


@pytest.mark.parametrize("dry_run, verb", [(True, "SELECT count(*)"), (False, "UPDATE")])
def test_normalize_renames_both_tables_from_the_canonical_season(dry_run, verb):
    session = FakeSession({}, usages=[("AJ Brown", "WR", 2024, 2025, False), ("A.J. Brown", "WR", 2018, 2026, True)])
    ((rename, counts),) = normalize_names(session, dry_run=dry_run)

    assert rename == Rename("WR", "AJ Brown", "A.J. Brown", 2018)
    assert counts == {"player_salaries": 3 if dry_run else 2, "player_projections": 3 if dry_run else 2}
    statements = [(sql, params) for sql, params in session.executed if params]
    assert [sql.strip().startswith(verb) for sql, _ in statements] == [True, True]
    assert statements[0][1] == {"old": "AJ Brown", "new": "A.J. Brown", "position": "WR", "from_year": 2018}
