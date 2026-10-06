// How hard a player's matchup is. The API ranks the opponent among all 32
// teams by the FPTS it allowed to the player's position per game over the
// last four weeks: 1st allowed the fewest (toughest), 32nd the most.

export const TEAMS = 32;

// Bottom-10 and top-10, as the Matchup column colors them.
export const matchupTier = (rank) => {
    if (rank === null || rank === undefined) return '';
    if (rank <= 10) return 'matchup-tough';
    if (rank >= TEAMS - 9) return 'matchup-soft';
    return '';
};

export const ordinal = (n) => {
    const suffixes = { one: 'st', two: 'nd', few: 'rd', other: 'th' };
    return `${n}${suffixes[new Intl.PluralRules('en-US', { type: 'ordinal' }).select(n)]}`;
};

// "the 7th fewest" / "the fewest" / "the 3rd most", whichever end is nearer.
const rankPhrase = (rank) => {
    if (rank === 1) return 'the fewest';
    if (rank === TEAMS) return 'the most';
    return rank <= TEAMS / 2 ? `the ${ordinal(rank)} fewest` : `the ${ordinal(TEAMS + 1 - rank)} most`;
};

// "CLE allows 17.1 FPTS a game to RBs, the 7th fewest (last 3 games)"
export const matchupSummary = ({
    opponent, position, opp_fpts_allowed: allowed, opp_fpts_allowed_rank: rank, opp_games: games,
}) => {
    if (rank === null || rank === undefined || allowed === null || allowed === undefined) return null;
    const verb = position === 'DST' ? 'gives up' : 'allows';
    return `${opponent} ${verb} ${allowed.toFixed(1)} FPTS a game to ${position}s, ${rankPhrase(rank)}`
        + ` (${games === 1 ? '1 game' : `${games} games`})`;
};
