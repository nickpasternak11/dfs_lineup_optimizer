import { formatSpread, linesSummary } from './lines';

test('spreads read betting-style', () => {
    expect([-7, 2.5, 0, null].map(formatSpread)).toEqual(['−7', '+2.5', 'PK', null]);
});

test('the summary gives both sides of the implied total', () => {
    const buffalo = { team: 'BUF', opponent: 'NE', game_total: 49.5, team_spread: -7, implied_total: 28.25 };
    expect(linesSummary(buffalo)).toBe('BUF −7 · O/U 49.5 · implied BUF 28.3, NE 21.3');
    expect(linesSummary({ ...buffalo, implied_total: null })).toBeNull();
});
