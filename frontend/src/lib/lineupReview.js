// Names and numbers for the weekly lineup review.

export const SOURCE_LABELS = { fantasypros: 'FantasyPros', model: 'Our model' };
export const STRATEGY_LABELS = { projection: 'Projection', blend_90_10: '90/10 blend', blend_80_20: '80/20 blend' };

export const lineupLabel = ({ source, strategy }) => (
    `${SOURCE_LABELS[source] || source} · ${STRATEGY_LABELS[strategy] || strategy}`
);

export const lineupKey = ({ source, strategy }) => `${source}:${strategy}`;

// "72%": a lineup's points as a share of the hindsight best.
export const shareOfBest = (actual, best) => (best ? `${Math.round((actual / best) * 100)}%` : '–');

// "Sun, Oct 11, 9:00 AM ET"
export const formatSavedAt = iso => `${new Date(iso).toLocaleString('en-US', {
    timeZone: 'America/New_York',
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
})} ET`;

// Each lineup with its two saves side by side: `initial` (before the week's
// first game) and `swap` (Sunday's late swap, when there was one).
export const pairLineups = (lineups) => {
    const pairs = new Map();
    lineups.forEach((lineup) => {
        const key = lineupKey(lineup);
        const pair = pairs.get(key) || { key, source: lineup.source, strategy: lineup.strategy };
        pair[lineup.phase === 'late_swap' ? 'swap' : 'initial'] = lineup;
        pairs.set(key, pair);
    });
    return [...pairs.values()];
};

// The lineup as played: after Sunday's swaps when they were made.
export const finalLineup = pair => pair.swap || pair.initial;

const average = values => (values.length ? values.reduce((a, b) => a + b, 0) / values.length : null);

// Over the season's finished weeks, per lineup: the average points as played,
// and the average swing from Sunday's swaps (weeks that had one).
export const seasonSummary = (season) => {
    const finished = season.filter(week => week.complete);
    const played = {};
    const swings = {};
    finished.forEach(week => pairLineups(week.lineups).forEach((pair) => {
        (played[pair.key] = played[pair.key] || []).push(finalLineup(pair).actual);
        if (pair.swap && pair.initial) (swings[pair.key] = swings[pair.key] || []).push(pair.swap.actual - pair.initial.actual);
    }));
    const averages = Object.fromEntries(Object.entries(played).map(([key, values]) => [key, average(values)]));
    const swapGains = Object.fromEntries(Object.entries(swings).map(([key, values]) => [key, average(values)]));
    return { averages, swapGains };
};

// "+4.2" / "−1.0"
export const formatSwing = value => (
    value === null || value === undefined ? '–' : `${value >= 0 ? '+' : '−'}${Math.abs(value).toFixed(1)}`
);
