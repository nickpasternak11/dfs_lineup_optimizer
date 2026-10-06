import { matchupSummary, matchupTier, ordinal } from './matchup';

test('ordinals', () => {
    expect([1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 32].map(ordinal)).toEqual(
        ['1st', '2nd', '3rd', '4th', '11th', '12th', '13th', '21st', '22nd', '23rd', '32nd'],
    );
});

test('the ten toughest and ten softest matchups are marked', () => {
    expect(matchupTier(1)).toBe('matchup-tough');
    expect(matchupTier(10)).toBe('matchup-tough');
    expect(matchupTier(11)).toBe('');
    expect(matchupTier(22)).toBe('');
    expect(matchupTier(23)).toBe('matchup-soft');
    expect(matchupTier(32)).toBe('matchup-soft');
    expect(matchupTier(null)).toBe('');
});

const rb = { opponent: 'CLE', position: 'RB', opp_fpts_allowed: 17.07, opp_games: 3 };

test('the summary counts from whichever end is nearer', () => {
    expect(matchupSummary({ ...rb, opp_fpts_allowed_rank: 7 }))
        .toBe('CLE allows 17.1 FPTS a game to RBs, the 7th fewest (3 games)');
    expect(matchupSummary({ ...rb, opp_fpts_allowed_rank: 1 })).toMatch(/RBs, the fewest/);
    expect(matchupSummary({ ...rb, opp_fpts_allowed_rank: 30 })).toMatch(/RBs, the 3rd most/);
    expect(matchupSummary({ ...rb, opp_fpts_allowed_rank: 32 })).toMatch(/RBs, the most/);
});

test('a defense faces an offense, which gives up points to DSTs', () => {
    expect(matchupSummary({ ...rb, position: 'DST', opp_fpts_allowed: 6.33, opp_fpts_allowed_rank: 17, opp_games: 1 }))
        .toBe('CLE gives up 6.3 FPTS a game to DSTs, the 16th most (1 game)');
    expect(matchupSummary({ ...rb, opp_fpts_allowed_rank: null })).toBeNull();
});
