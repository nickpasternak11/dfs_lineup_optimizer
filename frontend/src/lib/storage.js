// Browser storage can be missing or throw (private windows, blocked site
// data), so every access falls back quietly.

// v2: a map of "year-week" to excluded player names. The v1 key held one flat
// list with no week, which can't be safely assigned to one, so it's ignored.
const EXCLUDED_PLAYERS_KEY = 'dfs-lineup-optimizer-excluded-players-v2';
const THEME_KEY = 'dfs-lineup-optimizer-theme';

export const slateKey = (year, week) => `${year || 'unknown'}-${week || 'unknown'}`;

const read = (key) => {
    try {
        return window.localStorage.getItem(key);
    } catch (error) {
        return null;
    }
};

const write = (key, value) => {
    try {
        window.localStorage.setItem(key, value);
    } catch (error) {
        // Not persisted; the in-memory state still works for this visit.
    }
};

export const loadExcludedPlayers = () => {
    try {
        const parsed = JSON.parse(read(EXCLUDED_PLAYERS_KEY) || '{}');
        return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
    } catch (error) {
        return {};
    }
};

export const saveExcludedPlayers = map => write(EXCLUDED_PLAYERS_KEY, JSON.stringify(map));

export const loadTheme = () => {
    const theme = read(THEME_KEY);
    return theme === 'light' || theme === 'dark' ? theme : null;
};

export const saveTheme = theme => write(THEME_KEY, theme);
