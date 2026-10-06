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

// Each saved lineup's average over its finished weeks, for the season
// table's last row.
export const seasonAverages = (season) => {
    const sums = {};
    season.filter(week => week.complete).forEach(week => week.lineups.forEach((lineup) => {
        const key = lineupKey(lineup);
        sums[key] = sums[key] || { total: 0, weeks: 0 };
        sums[key].total += lineup.actual;
        sums[key].weeks += 1;
    }));
    return Object.fromEntries(Object.entries(sums).map(([key, { total, weeks }]) => [key, total / weeks]));
};
