// Formatting and grouping for the player popup's bio and game log.

export const formatHeight = inches => (
    inches ? `${Math.floor(inches / 12)}'${inches % 12}"` : null
);

export const ageOn = (birthdate, today = new Date()) => {
    if (!birthdate) return null;
    const [year, month, day] = birthdate.split('-').map(Number);
    let age = today.getFullYear() - year;
    const beforeBirthday = today.getMonth() + 1 < month
        || (today.getMonth() + 1 === month && today.getDate() < day);
    if (beforeBirthday) age -= 1;
    return age;
};

export const formatDraft = ({ draft_year: year, draft_round: round, draft_pick: pick } = {}) => {
    if (!year) return null;
    if (!round) return `${year} · Undrafted`;
    return `${year} · Rd ${round}${pick ? `, #${pick} overall` : ''}`;
};

// nflverse numbers postseason weeks on from the regular season (19-22).
export const weekLabel = game => (game.season_type === 'POST' ? `P${game.week}` : `W${game.week}`);

export const opponentLabel = (game) => {
    if (!game.opponent) return '';
    if (game.home === null || game.home === undefined) return game.opponent;
    return `${game.home ? 'vs' : '@'} ${game.opponent}`;
};

export const resultLabel = (game) => {
    const { team_score: ours, opponent_score: theirs } = game;
    if (ours === null || ours === undefined || theirs === null || theirs === undefined) return '';
    const outcome = ours > theirs ? 'W' : ours < theirs ? 'L' : 'T';
    return `${outcome} ${ours}–${theirs}`;
};

export const seasonsOf = games => [...new Set(games.map(g => g.year))].sort((a, b) => b - a);

// The slate's season when it has games yet; otherwise the latest that does,
// so week 1 opens on last season rather than an empty chart.
export const defaultSeason = (games, slateYear) => {
    const seasons = seasonsOf(games);
    return seasons.includes(Number(slateYear)) ? Number(slateYear) : seasons[0];
};

const average = values => (values.length ? values.reduce((a, b) => a + b, 0) / values.length : null);

export const seasonSummary = (games) => {
    const points = games.map(g => g.dk_points);
    const projected = games.filter(g => g.proj_fpts !== null && g.proj_fpts !== undefined);
    return {
        games: games.length,
        average: average(points),
        best: points.length ? Math.max(...points) : null,
        // Average of actual minus projection, over weeks we projected.
        vsProjection: projected.length
            ? average(projected.map(g => g.dk_points - g.proj_fpts))
            : null,
    };
};
