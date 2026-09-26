import pytest
from src.utils import get_player_injuries, get_stats, get_weekly_rankings


def test_rankings_are_parsed_from_the_embedded_ecr_data(fake_fetch):
    calls = fake_fetch("rankings_qb.html")

    df = get_weekly_rankings("QB", 2025, 3).set_index("player")

    url, params = calls[0]
    assert url.endswith("/nfl/rankings/qb.php")
    assert params == {"year": 2025, "week": 3}

    lamar = df.loc["Lamar Jackson"]
    assert (lamar["position"], lamar["rank"], lamar["grade"]) == ("QB", 1, "A+")
    assert (lamar["min_rank"], lamar["max_rank"]) == (1, 3)
    assert (lamar["avg_rank"], lamar["std_rank"], lamar["proj_fpts"]) == (1.4, 0.6, 24.0)
    assert (lamar["year"], lamar["week"]) == (2025, 3)


def test_rankings_skip_malformed_entries_and_default_missing_points(fake_fetch):
    fake_fetch("rankings_qb.html")

    players = set(get_weekly_rankings("QB", 2025, 3)["player"])

    # No start/sit grade: skipped rather than aborting the page.
    assert "Unranked Backup" not in players
    # No projected points: kept with 0.0.
    assert "Rookie Starter" in players


@pytest.mark.parametrize(
    "position, page",
    [("QB", "qb.php"), ("DST", "dst.php"), ("RB", "ppr-rb.php"), ("WR", "ppr-wr.php")],
)
def test_rankings_use_ppr_pages_for_skill_positions(fake_fetch, position, page):
    calls = fake_fetch("rankings_qb.html")
    get_weekly_rankings(position, 2025, 3)
    assert calls[0][0].endswith(f"/nfl/rankings/{page}")


def test_rankings_page_without_ecr_data_returns_nothing(fake_fetch):
    fake_fetch("injuries.html")
    assert get_weekly_rankings("QB", 2025, 3).empty


def test_stats_averages_per_game(fake_fetch):
    calls = fake_fetch("stats_dst.html")

    df = get_stats("DST", 2025, [1, 2]).set_index("player")

    assert calls[0][1]["start_week"] == 1
    assert calls[0][1]["end_week"] == 2

    bills = df.loc["Buffalo Bills"]
    assert bills["avg_fpts"] == 11.0
    assert bills["avg_sack"] == 3.0  # 6 sacks over 2 games
    assert bills["rost"] == 85.5
    assert bills["week"] == 3
    assert "fpts" not in df.columns


def test_week_one_stats_come_from_the_whole_previous_season(fake_fetch):
    calls = fake_fetch("stats_dst.html")
    get_stats("DST", 2025, [-3, 0])
    params = calls[0][1]
    assert (params["year"], params["start_week"], params["end_week"]) == (2024, 1, 18)


def test_injuries_are_requested_for_the_target_week(fake_fetch):
    calls = fake_fetch("injuries.html")
    get_player_injuries(2018, 3)
    assert calls[0][1] == {"year": 2018, "week": 3}


def test_injuries_keep_player_status_and_type(fake_fetch):
    fake_fetch("injuries.html")

    df = get_player_injuries(2025, 3).set_index("player")

    # The team suffix is dropped from the name; non-injury tables are ignored.
    assert list(df.index) == ["Brock Purdy", "Aaron Rodgers", "Christian McCaffrey"]
    assert list(df.columns) == ["injury_status", "injury_type"]
    assert tuple(df.loc["Brock Purdy"]) == ("Questionable", "Shoulder")
    assert tuple(df.loc["Aaron Rodgers"]) == ("Out", "")
