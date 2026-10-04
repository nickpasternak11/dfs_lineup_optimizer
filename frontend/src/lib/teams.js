// Team abbreviations as the salary scraper stores them, mapped to ESPN's logo
// codes and a primary color for the fallback badge. Older seasons use a few
// codes that have since changed (JAX/JAC, OAK), so those are aliased.
const TEAMS = {
    ARI: { name: 'Arizona Cardinals', espn: 'ari', color: '#97233F' },
    ATL: { name: 'Atlanta Falcons', espn: 'atl', color: '#A71930' },
    BAL: { name: 'Baltimore Ravens', espn: 'bal', color: '#241773' },
    BUF: { name: 'Buffalo Bills', espn: 'buf', color: '#00338D' },
    CAR: { name: 'Carolina Panthers', espn: 'car', color: '#0085CA' },
    CHI: { name: 'Chicago Bears', espn: 'chi', color: '#0B162A' },
    CIN: { name: 'Cincinnati Bengals', espn: 'cin', color: '#FB4F14' },
    CLE: { name: 'Cleveland Browns', espn: 'cle', color: '#311D00' },
    DAL: { name: 'Dallas Cowboys', espn: 'dal', color: '#003594' },
    DEN: { name: 'Denver Broncos', espn: 'den', color: '#FB4F14' },
    DET: { name: 'Detroit Lions', espn: 'det', color: '#0076B6' },
    GB: { name: 'Green Bay Packers', espn: 'gb', color: '#203731' },
    HOU: { name: 'Houston Texans', espn: 'hou', color: '#03202F' },
    IND: { name: 'Indianapolis Colts', espn: 'ind', color: '#002C5F' },
    JAX: { name: 'Jacksonville Jaguars', espn: 'jax', color: '#006778' },
    KC: { name: 'Kansas City Chiefs', espn: 'kc', color: '#E31837' },
    LAC: { name: 'Los Angeles Chargers', espn: 'lac', color: '#0080C6' },
    LAR: { name: 'Los Angeles Rams', espn: 'lar', color: '#003594' },
    LV: { name: 'Las Vegas Raiders', espn: 'lv', color: '#000000' },
    MIA: { name: 'Miami Dolphins', espn: 'mia', color: '#008E97' },
    MIN: { name: 'Minnesota Vikings', espn: 'min', color: '#4F2683' },
    NE: { name: 'New England Patriots', espn: 'ne', color: '#002244' },
    NO: { name: 'New Orleans Saints', espn: 'no', color: '#9F8958' },
    NYG: { name: 'New York Giants', espn: 'nyg', color: '#0B2265' },
    NYJ: { name: 'New York Jets', espn: 'nyj', color: '#125740' },
    PHI: { name: 'Philadelphia Eagles', espn: 'phi', color: '#004C54' },
    PIT: { name: 'Pittsburgh Steelers', espn: 'pit', color: '#101820' },
    SEA: { name: 'Seattle Seahawks', espn: 'sea', color: '#002244' },
    SF: { name: 'San Francisco 49ers', espn: 'sf', color: '#AA0000' },
    TB: { name: 'Tampa Bay Buccaneers', espn: 'tb', color: '#D50A0A' },
    TEN: { name: 'Tennessee Titans', espn: 'ten', color: '#0C2340' },
    WAS: { name: 'Washington Commanders', espn: 'wsh', color: '#5A1414' },
};

const ALIASES = { JAC: 'JAX', WSH: 'WAS', OAK: 'LV', LA: 'LAR', SD: 'LAC' };

export const getTeam = (abbreviation) => {
    const code = String(abbreviation || '').toUpperCase();
    const team = TEAMS[ALIASES[code] || code];
    return team ? { abbreviation: code, ...team } : null;
};

// ESPN's "500-dark" set has versions of the darker logos that stay visible
// on a dark background.
export const teamLogoUrl = (abbreviation, theme = 'light') => {
    const team = getTeam(abbreviation);
    const set = theme === 'dark' ? '500-dark' : '500';
    return team ? `https://a.espncdn.com/i/teamlogos/nfl/${set}/${team.espn}.png` : null;
};

// 70x70 is the smallest FantasyPros serves; enough for a 40px avatar at 2x.
export const headshotUrl = (fpPlayerId) => (
    fpPlayerId ? `https://images.fantasypros.com/images/players/nfl/${fpPlayerId}/headshot/70x70.png` : null
);
