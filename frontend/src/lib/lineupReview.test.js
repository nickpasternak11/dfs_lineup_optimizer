import {
    finalLineup, formatSavedAt, formatSwing, lineupLabel, pairLineups, seasonSummary, shareOfBest,
} from './lineupReview';

test('labels and shares', () => {
    expect(lineupLabel({ source: 'model', strategy: 'blend_90_10' })).toBe('Our model · 90/10 blend');
    expect(shareOfBest(126, 180)).toBe('70%');
    expect(shareOfBest(126, null)).toBe('–');
});

test('saved times read in Eastern time', () => {
    expect(formatSavedAt('2026-10-11T13:00:00Z')).toBe('Sun, Oct 11, 9:00 AM ET');
});

const saved = (phase, source, actual) => ({ phase, source, strategy: 'projection', projected: 100, actual });

test('the two saves of a lineup pair up, and the swap is what was played', () => {
    const [pair] = pairLineups([saved('initial', 'model', 100), saved('late_swap', 'model', 108)]);
    expect(pair.initial.actual).toBe(100);
    expect(finalLineup(pair).actual).toBe(108);
    expect(finalLineup(pairLineups([saved('initial', 'model', 100)])[0]).actual).toBe(100);
});

test('season averages as played, and the swing from swaps, over finished weeks only', () => {
    const season = [
        { week: 5, complete: true, lineups: [saved('initial', 'model', 120)] },
        { week: 6, complete: true, lineups: [saved('initial', 'model', 90), saved('late_swap', 'model', 100), saved('initial', 'fantasypros', 90)] },
        { week: 7, complete: false, lineups: [saved('initial', 'model', 12)] },
    ];
    const { averages, swapGains } = seasonSummary(season);
    expect(averages).toEqual({ 'model:projection': 110, 'fantasypros:projection': 90 });
    expect(swapGains).toEqual({ 'model:projection': 10 });
    expect([formatSwing(4.24), formatSwing(-1), formatSwing(null)]).toEqual(['+4.2', '−1.0', '–']);
});
