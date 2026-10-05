import { niceScale } from './chartScale';

test('ticks are round numbers from zero', () => {
    expect(niceScale(0, 35.66)).toEqual({ min: 0, max: 40, ticks: [0, 10, 20, 30, 40] });
});

test('small ranges get finer steps', () => {
    expect(niceScale(0, 7).ticks).toEqual([0, 2, 4, 6, 8]);
});

test('negative scores extend the axis below zero', () => {
    const scale = niceScale(-4, 13);
    expect(scale.min).toBeLessThan(0);
    expect(scale.ticks).toContain(0);
    expect(scale.min).toBeLessThanOrEqual(-4);
});

test('an all-zero season still has an axis', () => {
    expect(niceScale(0, 0).max).toBeGreaterThan(0);
});
