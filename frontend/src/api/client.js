import axios from 'axios';

// The API listens on port 8080 of whichever host served the page.
export const API_URL = `${window.location.protocol}//${window.location.hostname}:8080`;

const toInt = value => (value ? parseInt(value, 10) : null);

export const fetchCurrentSlate = async () => {
    const [year, week] = await Promise.all([
        axios.get(`${API_URL}/projections/current_year`),
        axios.get(`${API_URL}/projections/current_week`),
    ]);
    return { year: String(year.data), week: String(week.data) };
};

export const fetchProjections = async (year, week) => {
    const response = await axios.post(`${API_URL}/projections`, { year: toInt(year), week: toInt(week) });
    return response.data;
};

export const fetchLineups = async ({ year, week, stackQbCount, avoidTeFlex, includeStarted, excluded, locked }) => {
    const response = await axios.post(`${API_URL}/optimize`, {
        year: toInt(year),
        week: toInt(week),
        stack_qb_count: stackQbCount,
        avoid_te_flex: avoidTeFlex,
        include_started_players: includeStarted,
        excluded_players: excluded,
        included_players: locked,
    });
    return response.data;
};

export const fetchPlayerGameLog = async (gsisId) => {
    const response = await axios.get(`${API_URL}/game-logs/players/${encodeURIComponent(gsisId)}`);
    return response.data;
};

export const fetchDstGameLog = async (team) => {
    const response = await axios.get(`${API_URL}/game-logs/dst/${encodeURIComponent(team)}`);
    return response.data;
};

export const fetchAccuracy = async ({ view, year, position, minProj }) => {
    const response = await axios.get(`${API_URL}/accuracy`, {
        params: { view, year: year ?? undefined, position: position ?? undefined, min_proj: minProj },
    });
    return response.data;
};

// FastAPI puts a string in `detail` for HTTPExceptions and a list for
// validation errors.
export const errorMessage = (error, fallback) => {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
    return fallback;
};
