import {
    biasSentence, compareMetric, differenceLabel, formatMetric, rangeLabel, tierLabel,
} from './accuracy';

test('metrics format in their own units', () => {
    expect(formatMetric('mae', 5.841)).toBe('5.8');
    expect(formatMetric('within', 0.534)).toBe('53%');
    expect(formatMetric('rank_corr', 0.4127)).toBe('0.41');
    expect(formatMetric('bias', 0.434)).toBe('+0.4');
    expect(formatMetric('bias', -0.167)).toBe('−0.2');
    expect(formatMetric('bias', -0.04)).toBe('0.0');
    expect(formatMetric('rank_corr', null)).toBe('–');
});

test('lower misses and higher rankings are better; bias has no better side', () => {
    expect(compareMetric('mae', 5.8, 6.6)).toBe(1);
    expect(compareMetric('within', 0.48, 0.53)).toBe(-1);
    expect(compareMetric('rank_corr', 0.41, 0.27)).toBe(1);
    expect(compareMetric('bias', 0.4, -0.2)).toBe(0);
    expect(compareMetric('mae', 5.8, null)).toBe(0);
});

test('the difference reads in the metric units', () => {
    expect(differenceLabel('mae', 5.841, 6.637)).toBe('0.8 FPTS better');
    expect(differenceLabel('within', 0.482, 0.534)).toBe('5 pts worse');
    expect(differenceLabel('rank_corr', 0.413, 0.265)).toBe('0.15 better');
    expect(differenceLabel('bias', 0.4, -0.2)).toBeNull();
});

test('bias in words', () => {
    expect(biasSentence(0.434)).toBe('Players beat it by 0.4 FPTS on average');
    expect(biasSentence(-1.26)).toBe('Players fell 1.3 FPTS short on average');
    expect(biasSentence(0.01)).toBe('Players scored what it projected, on average');
});

test('ranges and salary tiers', () => {
    expect([{ low: null, high: 5 }, { low: 10, high: 15 }, { low: 25, high: null }].map(rangeLabel))
        .toEqual(['Under 5', '10–15', '25+']);
    expect([{ low: null, high: 4000 }, { low: 4000, high: 6000 }, { low: 8000, high: null }].map(tierLabel))
        .toEqual(['Under $4,000', '$4,000–$5,900', '$8,000+']);
});
