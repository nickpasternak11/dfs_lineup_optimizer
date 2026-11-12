// DraftKings NFL classic: QB, 2 RB, 3 WR, TE, FLEX (RB/WR/TE), DST.
export const SALARY_CAP = 50000;
export const ROSTER_SIZE = 9;
export const POSITIONS = ['QB', 'RB', 'WR', 'TE', 'DST'];
export const FIRST_SEASON = 2018;
export const WEEKS_PER_SEASON = 18;

// One suggested lineup per projection source. In a 2018-2026 lineup backtest
// the three built lineups of about the same quality, and every blend with the
// recent average built worse ones, so there are none.
export const LINEUP_SOURCES = [
    { source: 'fantasypros', label: 'FantasyPros', detail: 'Optimized on FantasyPros projections.' },
    { source: 'model', label: 'Our model', detail: 'Optimized on our model\'s projections.' },
    { source: 'average', label: 'FP + model', detail: 'Optimized on the average of FantasyPros and our model.' },
];

export const KICKOFF_CUTOFFS = [
    { value: '', label: 'All games' },
    { value: 'friday', label: 'Friday or later' },
    { value: 'sunday', label: 'Sunday or later' },
    { value: 'sunday_main', label: 'Sunday main slate (1 PM+)' },
];

export const VALUE_PLAY_THRESHOLD = 2.5;
