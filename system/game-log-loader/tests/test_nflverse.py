import gzip
from types import SimpleNamespace

import pandas as pd
import pytest
from src import nflverse


@pytest.fixture
def player_logs(nflverse_files):
    return nflverse.player_game_logs(nflverse_files["player_stats"]).set_index("player")


# Expected DraftKings points are worked by hand from each stat line.
@pytest.mark.parametrize(
    "player, dk_points",
    [
        # 318 pass yds (12.72 + 3 bonus), 1 TD, 1 INT (-1), 60 rush yds, 1 rush TD
        ("Patrick Mahomes", 30.72),
        # 206 rush yds (20.6 + 3 bonus), 1 TD; 3 catches for 28
        ("Rico Dowdle", 35.4),
        # 1 catch for 6, plus an offensive fumble-recovery TD
        ("Tyler Lockett", 7.6),
        # 7 catches for 61, 1 TD
        ("Travis Kelce", 19.1),
    ],
)
def test_player_draftkings_points(player_logs, player, dk_points):
    assert player_logs.loc[player, "dk_points"] == pytest.approx(dk_points)


def test_only_fantasy_positions_are_kept(player_logs):
    assert set(player_logs.position) == {"QB", "RB", "WR", "TE"}
    assert "Matt Prater" not in player_logs.index  # K
    assert "Von Miller" not in player_logs.index  # OLB


def test_player_logs_keep_ids_context_and_nflverse_ppr(player_logs):
    mahomes = player_logs.loc["Patrick Mahomes"]
    assert (mahomes.year, mahomes.week, mahomes.team, mahomes.opponent) == (2025, 5, "KC", "JAX")
    assert mahomes.gsis_id == "00-0033873"
    assert mahomes.game_id == "2025_05_KC_JAX"
    assert mahomes.ppr_points == pytest.approx(26.72)
    assert (mahomes.interceptions, mahomes.passing_yards) == (1, 318)


@pytest.fixture
def dst_logs(nflverse_files):
    return nflverse.dst_game_logs(nflverse_files["team_stats"], nflverse_files["games"]).set_index("team")


@pytest.mark.parametrize(
    "team, points_allowed, dk_points",
    [
        ("JAX", 28, 7),  # 1 INT, 1 defensive TD, 28 allowed (-1)
        ("KC", 31, 6),  # 3 sacks, 1 INT, 1 fumble recovery, 31 allowed (-1)
        ("WAS", 10, 13),  # away team: allowed LAC's 10 (+4); 5 sacks, INT, FR
        ("LAC", 27, 3),  # home team: allowed WAS's 27 (0); 1 sack, FR
    ],
)
def test_dst_draftkings_points(dst_logs, team, points_allowed, dk_points):
    assert dst_logs.loc[team, "points_allowed"] == points_allowed
    assert dst_logs.loc[team, "dk_points"] == pytest.approx(dk_points)


def test_dst_weeks_without_a_final_score_are_left_out(nflverse_files):
    team_stats = nflverse_files["team_stats"].head(1).copy()
    team_stats["game_id"] = "2026_04_TEN_BAL"  # no score yet in the fixture
    assert nflverse.dst_game_logs(team_stats, nflverse_files["games"]).empty


def test_games_convert_eastern_kickoffs_to_utc(nflverse_files):
    games = nflverse.nfl_games(nflverse_files["games"], 2025).set_index("game_id")
    # Monday 8:15 PM Eastern (EDT) is Tuesday 00:15 UTC.
    assert games.loc["2025_05_KC_JAX", "kickoff"] == pd.Timestamp("2025-10-07 00:15", tz="UTC")
    assert games.loc["2025_05_KC_JAX", "home_score"] == 31
    assert games.loc["2025_05_TEN_ARI", "spread_line"] == 7.5
    assert set(games.year) == {2025}


def test_unplayed_games_keep_lines_and_null_scores(nflverse_files):
    game = nflverse.nfl_games(nflverse_files["games"], 2026).set_index("game_id").loc["2026_04_TEN_BAL"]
    assert pd.isna(game.home_score) and pd.isna(game.away_score)
    assert (game.spread_line, game.total_line, game.home_moneyline) == (11.5, 42.5, -800)


def test_nfl_players_collapse_repeats_and_drop_conflicts(nflverse_files):
    crosswalk = nflverse_files["player_ids"]
    # A FantasyPros id the crosswalk pairs with a second, different GSIS id.
    conflict = crosswalk[crosswalk.name == "Josh Allen"].assign(gsis_id="00-9999999")
    ids = nflverse.nfl_players(pd.concat([crosswalk, conflict])).set_index("gsis_id")

    # Listed twice (DT and S) with the same pair: kept once.
    assert ids.loc["00-0031636", "fp_player_id"] == 14066
    assert ids.loc["00-0033873", "fp_player_id"] == 16413
    # Josh Allen's FantasyPros id now points at two players: dropped.
    assert 17298 not in set(ids.fp_player_id)
    # No FantasyPros id: nothing to map.
    assert "00-0041152" not in ids.index
    assert ids.index.is_unique and ids.fp_player_id.is_unique


def test_read_csv_handles_gzip(monkeypatch):
    payload = gzip.compress(b"a,b\n1,2\n")
    monkeypatch.setattr(nflverse, "fetch", lambda url, timeout: SimpleNamespace(content=payload))
    assert nflverse.read_csv("https://example.test/x.csv.gz").to_dict("records") == [{"a": 1, "b": 2}]


def test_nfl_players_carry_bios(nflverse_files):
    allen = nflverse.nfl_players(nflverse_files["player_ids"]).set_index("gsis_id").loc["00-0034857"]
    assert (allen.player, str(allen.birthdate), allen.height, allen.weight) == ("Josh Allen", "1996-05-21", 77, 237)
    assert (allen.college, allen.draft_year, allen.draft_round, allen.draft_pick) == ("Wyoming", 2018, 1, 7)


def test_injury_reports_keep_game_status_and_practice(nflverse_files):
    reports = nflverse.injury_reports(nflverse_files["injuries"]).set_index("player")

    milano = reports.loc["Matt Milano"]
    assert (milano.year, milano.week, milano.team) == (2025, 5, "BUF")
    assert (milano.report_status, milano.practice_status) == ("Questionable", "Limited")
    assert (reports.loc["Dorian Williams", "report_status"], reports.loc["Dorian Williams", "practice_status"]) == ("Out", "DNP")
    # Practiced in full with no game status.
    assert pd.isna(reports.loc["Jackson Hawes", "report_status"])
    assert reports.loc["Jackson Hawes", "practice_status"] == "Full"
    # Probable (before 2016) stays; "Note" rows carry no status.
    assert reports.loc["Probable Player", "report_status"] == "Probable"
    assert pd.isna(reports.loc["Note Player", "report_status"]) and pd.isna(reports.loc["Note Player", "practice_status"])


def test_injury_reports_drop_missing_ids_and_keep_a_traded_players_later_row(nflverse_files):
    reports = nflverse.injury_reports(nflverse_files["injuries"])
    assert "No Id" not in set(reports.player)
    traded = reports[reports.player == "Traded Player"]
    assert list(zip(traded.team, traded.report_status)) == [("BUF", "Out")]
    assert not reports.duplicated(["year", "week", "gsis_id"]).any()


def test_injury_reports_load_from_2009(monkeypatch):
    requested = []
    monkeypatch.setattr(nflverse, "read_csv", lambda url: requested.append(url) or pd.DataFrame())
    nflverse.download_season(2008)
    assert not any("injuries" in url for url in requested)
    nflverse.download_season(2012)
    assert requested[-1].endswith("/injuries/injuries_2012.csv")


def test_injury_files_before_2025_have_no_season_type(nflverse_files):
    # 2009-2024 files carry game_type only.
    old_format = nflverse_files["injuries"].drop(columns="season_type").assign(game_type="WC")
    reports = nflverse.injury_reports(old_format)
    assert set(reports.season_type) == {"POST"}
    assert set(nflverse.injury_reports(nflverse_files["injuries"]).season_type) == {"REG"}
