// Formatting and comparisons for the accuracy page. The API reports metrics
// for each projection source; the first source is the one the optimizer
// uses, and the page measures the others against it.

// Rounded before signing, so -0.04 reads 0.0 rather than −0.0.
const signed = (value, digits) => {
    const rounded = Number(value.toFixed(digits));
    if (rounded === 0) return (0).toFixed(digits);
    return `${rounded > 0 ? '+' : '−'}${Math.abs(rounded).toFixed(digits)}`;
};

export const METRICS = {
    mae: {
        label: 'Average miss',
        better: 'lower',
        format: value => value.toFixed(1),
        // The difference between two sources, in the metric's own units.
        difference: diff => `${diff.toFixed(1)} FPTS`,
        description: 'How far off the projection was, on average, in either direction.',
    },
    within: {
        label: 'Within 5 FPTS',
        better: 'higher',
        format: value => `${Math.round(value * 100)}%`,
        difference: diff => `${Math.round(diff * 100)} pts`,
        description: 'Share of projections that landed within 5 FPTS of what the player scored.',
    },
    rank_corr: {
        label: 'Ranking',
        better: 'higher',
        format: value => value.toFixed(2),
        difference: diff => diff.toFixed(2),
        description: 'How well it ordered the players at each position each week: '
            + '1 is a perfect order, 0 no better than chance (Spearman correlation).',
    },
    bias: {
        label: 'Bias',
        better: null,
        format: value => signed(value, 1),
        difference: diff => diff.toFixed(1),
        description: 'Actual minus projected, on average: positive when players beat the projection.',
    },
};

const isMissing = value => value === null || value === undefined;

export const formatMetric = (metric, value) => (isMissing(value) ? '–' : METRICS[metric].format(value));

// 1 when `a` is better than `b` for the metric, -1 when worse, 0 when they're
// level or the metric has no better direction.
export const compareMetric = (metric, a, b) => {
    const { better } = METRICS[metric];
    if (!better || isMissing(a) || isMissing(b) || a === b) return 0;
    return (better === 'lower' ? a < b : a > b) ? 1 : -1;
};

// "0.8 FPTS better" / "5 pts worse": `a` measured against `b`.
export const differenceLabel = (metric, a, b) => {
    const verdict = compareMetric(metric, a, b);
    if (!verdict) return null;
    return `${METRICS[metric].difference(Math.abs(a - b))} ${verdict > 0 ? 'better' : 'worse'}`;
};

// The bias metric in words, for the summary tile.
export const biasSentence = (bias) => {
    if (isMissing(bias)) return null;
    if (Math.abs(bias) < 0.05) return 'Players scored what it projected, on average';
    return bias > 0
        ? `Players beat it by ${bias.toFixed(1)} FPTS on average`
        : `Players fell ${Math.abs(bias).toFixed(1)} FPTS short on average`;
};

// Projection ranges for calibration: "Under 5", "10–15", "25+".
export const rangeLabel = ({ low, high }) => {
    if (low === null) return `Under ${high}`;
    if (high === null) return `${low}+`;
    return `${low}–${high}`;
};

// Salary tiers: salaries move in $100 steps, so a tier ends $100 below the next.
export const tierLabel = ({ low, high }) => {
    const money = value => `$${value.toLocaleString('en-US')}`;
    if (low === null) return `Under ${money(high)}`;
    if (high === null) return `${money(low)}+`;
    return `${money(low)}–${money(high - 100)}`;
};

export const weekLabel = ({ year, week }) => `${year} W${week}`;

export const formatCount = value => value.toLocaleString('en-US');
