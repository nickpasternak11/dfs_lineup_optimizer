// Betting lines from the nflverse schedule: the game's over/under and the
// team's spread (favorites negative), which together imply each side's points.

export const formatSpread = (spread) => {
    if (spread === null || spread === undefined) return null;
    if (spread === 0) return 'PK';
    return spread > 0 ? `+${spread}` : `−${Math.abs(spread)}`;
};

// "BUF −7 · O/U 49.5 · implied BUF 28.3, NE 21.3"
export const linesSummary = ({
    team, opponent, game_total: total, team_spread: spread, implied_total: implied,
}) => {
    if (implied === null || implied === undefined) return null;
    return `${team} ${formatSpread(spread)} · O/U ${total}`
        + ` · implied ${team} ${implied.toFixed(1)}, ${opponent} ${(total - implied).toFixed(1)}`;
};
