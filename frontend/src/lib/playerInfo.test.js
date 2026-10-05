import {
    ageOn, defaultSeason, formatDraft, formatHeight, opponentLabel, resultLabel,
    seasonSummary, seasonsOf, weekLabel,
} from './playerInfo';

test('height in feet and inches', () => {
    expect(formatHeight(77)).toBe('6\'5"');
    expect(formatHeight(72)).toBe('6\'0"');
    expect(formatHeight(null)).toBeNull();
});

test('age counts only birthdays that have passed', () => {
    const today = new Date(2026, 9, 4); // Oct 4, 2026
    expect(ageOn('1996-05-21', today)).toBe(30);
    expect(ageOn('2000-10-05', today)).toBe(25);
    expect(ageOn('2000-10-04', today)).toBe(26);
    expect(ageOn(null, today)).toBeNull();
});

test('draft line', () => {
    expect(formatDraft({ draft_year: 2018, draft_round: 1, draft_pick: 7 })).toBe('2018 · Rd 1, #7 overall');
    expect(formatDraft({ draft_year: 2021, draft_round: null, draft_pick: null })).toBe('2021 · Undrafted');
    expect(formatDraft({ draft_year: null })).toBeNull();
});

const game = (year, week, extra = {}) => ({
    year, week, season_type: 'REG', opponent: 'NYJ', home: false,
    team_score: 30, opponent_score: 10, dk_points: 20, proj_fpts: null, ...extra,
});

test('game labels', () => {
    expect(weekLabel(game(2025, 3))).toBe('W3');
    expect(weekLabel(game(2025, 20, { season_type: 'POST' }))).toBe('P20');
    expect(opponentLabel(game(2025, 3))).toBe('@ NYJ');
    expect(opponentLabel(game(2025, 3, { home: true }))).toBe('vs NYJ');
    expect(resultLabel(game(2025, 3))).toBe('W 30–10');
    expect(resultLabel(game(2025, 3, { team_score: 17, opponent_score: 24 }))).toBe('L 17–24');
    expect(resultLabel(game(2025, 3, { team_score: null }))).toBe('');
});

test('the popup opens on the slate season, or the latest one with games', () => {
    const games = [game(2024, 1), game(2025, 1), game(2025, 2)];
    expect(seasonsOf(games)).toEqual([2025, 2024]);
    expect(defaultSeason(games, '2025')).toBe(2025);
    // Week 1 of 2026, before any games: show last season.
    expect(defaultSeason(games, '2026')).toBe(2025);
});

test('season summary compares with projections only where we had them', () => {
    const summary = seasonSummary([
        game(2025, 1, { dk_points: 30, proj_fpts: 20 }),
        game(2025, 2, { dk_points: 10, proj_fpts: 20 }),
        game(2025, 3, { dk_points: 26 }),
    ]);
    expect(summary).toEqual({ games: 3, average: 22, best: 30, vsProjection: 0 });
});
