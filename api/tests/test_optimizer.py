import math

import pandas as pd
import pytest

SALARY_CAP = 50000


def position_counts(lineup: pd.DataFrame) -> dict:
    return lineup["position"].value_counts().to_dict()


def assert_valid_roster(lineup: pd.DataFrame) -> None:
    counts = position_counts(lineup)
    assert len(lineup) == 9
    assert counts.get("QB") == 1
    assert counts.get("DST") == 1
    assert 2 <= counts.get("RB", 0) <= 3
    assert 3 <= counts.get("WR", 0) <= 4
    assert 1 <= counts.get("TE", 0) <= 2
    # Exactly one FLEX: seven RB/WR/TE in total.
    assert counts.get("RB", 0) + counts.get("WR", 0) + counts.get("TE", 0) == 7
    assert lineup["salary"].sum() <= SALARY_CAP


def test_lineup_is_a_valid_draftkings_roster(pool, make_optimizer):
    assert_valid_roster(make_optimizer(pool).optimize())


def test_lineup_takes_the_highest_projections_when_salary_allows(pool, make_optimizer):
    lineup = make_optimizer(pool).optimize()
    assert set(lineup["player"]) >= {"QB A1", "RB A1", "WR A1", "TE A1", "DST A"}


def test_salary_cap_forces_cheaper_players(pool, make_optimizer):
    # Nine $6,000 players would cost $54,000, so the cheap ones must be used.
    pool["salary"] = 6000
    cheap = ["RB E1", "WR E1", "TE C1"]
    pool.loc[pool["player"].isin(cheap), "salary"] = 3000

    lineup = make_optimizer(pool).optimize()

    assert_valid_roster(lineup)
    assert lineup["salary"].sum() <= SALARY_CAP


def test_two_tight_ends_allowed_in_flex_by_default(pool, make_optimizer):
    pool.loc[pool["player"].isin(["TE A1", "TE B1"]), "proj_fpts"] = 30.0
    lineup = make_optimizer(pool).optimize()
    assert position_counts(lineup)["TE"] == 2


def test_avoid_te_flex_keeps_one_tight_end(pool, make_optimizer):
    pool.loc[pool["player"].isin(["TE A1", "TE B1"]), "proj_fpts"] = 30.0
    lineup = make_optimizer(pool).optimize(avoid_te_flex=True)
    assert_valid_roster(lineup)
    assert position_counts(lineup)["TE"] == 1


def test_excluded_player_is_never_selected(pool, make_optimizer):
    lineup = make_optimizer(pool).optimize(excluded_players=["QB A1"])
    assert "QB A1" not in set(lineup["player"])
    assert_valid_roster(lineup)


def test_included_player_is_always_selected(pool, make_optimizer):
    lineup = make_optimizer(pool).optimize(included_players=["WR E1"])
    assert "WR E1" in set(lineup["player"])
    assert_valid_roster(lineup)


def test_unknown_included_player_is_rejected(pool, make_optimizer):
    with pytest.raises(ValueError, match="not found"):
        make_optimizer(pool).optimize(included_players=["Nobody"])


def test_qb_stack_pairs_the_qb_with_his_receivers(pool, make_optimizer):
    # Team B's QB is best, but its receivers aren't worth rostering on their
    # own; a two-man stack must pair the chosen QB with two same-team WR/TE.
    pool.loc[pool["player"] == "QB B1", "proj_fpts"] = 25.0
    pool.loc[pool["player"].isin(["WR B1", "TE B1"]), "proj_fpts"] = 1.0

    lineup = make_optimizer(pool).optimize(stack_qb_count=2)

    assert_valid_roster(lineup)
    qb_team = lineup.loc[lineup["position"] == "QB", "team"].iloc[0]
    receivers = lineup[(lineup["team"] == qb_team) & lineup["position"].isin(["WR", "TE"])]
    assert len(receivers) >= 2


def test_started_games_are_excluded_by_default(pool, make_optimizer):
    pool.loc[pool["player"] == "QB A1", "kickoff"] = pd.Timestamp("2020-01-01", tz="UTC")
    lineup = make_optimizer(pool).optimize()
    assert "QB A1" not in set(lineup["player"])


def test_started_games_can_be_included(pool, make_optimizer):
    pool.loc[pool["player"] == "QB A1", "kickoff"] = pd.Timestamp("2020-01-01", tz="UTC")
    lineup = make_optimizer(pool).optimize(include_started_players=True)
    assert "QB A1" in set(lineup["player"])


def test_missing_kickoff_counts_as_not_started(pool, make_optimizer):
    # Historical weeks have NULL kickoffs; they must stay eligible.
    assert pool["kickoff"].isna().all()
    assert_valid_roster(make_optimizer(pool).optimize())


def test_missing_avg_fpts_does_not_break_the_blended_lineups(pool, make_optimizer):
    # Regression: NULL avg_fpts made the blended score NaN and crashed pulp.
    pool.loc[pool["player"].isin(["QB A1", "RB A1", "WR A1"]), "avg_fpts"] = float("nan")

    lineups = make_optimizer(pool).get_optimal_lineups()

    assert len(lineups) == 3
    for lineup in lineups:
        assert len(lineup) == 9
        assert all(not math.isnan(player["proj_fpts"]) for player in lineup)


def test_empty_pool_is_reported_as_not_found(pool, make_optimizer):
    with pytest.raises(FileNotFoundError):
        make_optimizer(pool.iloc[0:0]).optimize()
