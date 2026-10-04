import { getTeam, headshotUrl, teamLogoUrl } from './teams';

const SCRAPED_TEAMS = [
    'ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE', 'DAL', 'DEN', 'DET',
    'GB', 'HOU', 'IND', 'JAC', 'JAX', 'KC', 'LAC', 'LAR', 'LV', 'MIA', 'MIN', 'NE',
    'NO', 'NYG', 'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WAS',
];

test('every team code in the database has a logo', () => {
    SCRAPED_TEAMS.forEach(code => expect(teamLogoUrl(code)).toMatch(/^https:\/\/a\.espncdn\.com\/.+\.png$/));
});

test('codes that differ from ESPN map to its logo names', () => {
    expect(teamLogoUrl('WAS')).toMatch(/\/wsh\.png$/);
    expect(teamLogoUrl('JAC')).toMatch(/\/jax\.png$/);
    expect(getTeam('jac').name).toBe('Jacksonville Jaguars');
});

test('dark mode uses the dark-background logo set', () => {
    expect(teamLogoUrl('LV', 'dark')).toBe('https://a.espncdn.com/i/teamlogos/nfl/500-dark/lv.png');
});

test('unknown or missing teams have no logo', () => {
    expect(getTeam('XYZ')).toBeNull();
    expect(teamLogoUrl(null)).toBeNull();
});

test('headshots need a FantasyPros id', () => {
    expect(headshotUrl(17298)).toBe('https://images.fantasypros.com/images/players/nfl/17298/headshot/70x70.png');
    expect(headshotUrl(null)).toBeNull();
});
