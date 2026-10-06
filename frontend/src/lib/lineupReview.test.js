import { formatSavedAt, lineupLabel, seasonAverages, shareOfBest } from './lineupReview';

test('labels and shares', () => {
    expect(lineupLabel({ source: 'model', strategy: 'blend_90_10' })).toBe('Our model · 90/10 blend');
    expect(shareOfBest(126, 180)).toBe('70%');
    expect(shareOfBest(126, null)).toBe('–');
});

test('saved times read in Eastern time', () => {
    expect(formatSavedAt('2026-10-11T13:00:00Z')).toBe('Sun, Oct 11, 9:00 AM ET');
});

test('season averages per lineup, over finished weeks only', () => {
    const season = [
        { week: 5, complete: true, lineups: [{ source: 'model', strategy: 'projection', actual: 120 }] },
        { week: 6, complete: true, lineups: [{ source: 'model', strategy: 'projection', actual: 100 }, { source: 'fantasypros', strategy: 'projection', actual: 90 }] },
        { week: 7, complete: false, lineups: [{ source: 'model', strategy: 'projection', actual: 12 }] },
    ];
    expect(seasonAverages(season)).toEqual({ 'model:projection': 110, 'fantasypros:projection': 90 });
});
