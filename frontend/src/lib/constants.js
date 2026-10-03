// DraftKings NFL classic: QB, 2 RB, 3 WR, TE, FLEX (RB/WR/TE), DST.
export const SALARY_CAP = 50000;
export const ROSTER_SIZE = 9;
export const POSITIONS = ['QB', 'RB', 'WR', 'TE', 'DST'];
export const FIRST_SEASON = 2018;
export const WEEKS_PER_SEASON = 18;

// The API returns three lineups, solved on increasingly more of each player's
// recent average blended into their projection (api/app/db/optimize.py).
export const LINEUP_STRATEGIES = [
    { label: 'Projection', detail: 'Optimized on FantasyPros projections alone.' },
    { label: '90/10 blend', detail: 'Optimized on 90% projection, 10% recent average.' },
    { label: '80/20 blend', detail: 'Optimized on 80% projection, 20% recent average.' },
];

export const KICKOFF_CUTOFFS = [
    { value: '', label: 'All games' },
    { value: 'friday', label: 'Friday or later' },
    { value: 'sunday', label: 'Sunday or later' },
    { value: 'sunday_main', label: 'Sunday main slate (1 PM+)' },
];

export const VALUE_PLAY_THRESHOLD = 2.5;
