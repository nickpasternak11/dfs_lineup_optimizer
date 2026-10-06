import { useEffect, useMemo, useState } from 'react';
import { VALUE_PLAY_THRESHOLD } from '../lib/constants';
import { defaultKickoffCutoff, hasKickoffPassed, satisfiesKickoffCutoff } from '../lib/kickoff';

const EMPTY_FILTERS = { search: '', position: '', team: '', opponent: '', cutoff: '', quick: '' };

// Re-renders every `ms` so "started" players move to Unavailable as their
// games kick off, without a reload.
const useNow = (ms) => {
    const [now, setNow] = useState(() => new Date());
    useEffect(() => {
        const timer = setInterval(() => setNow(new Date()), ms);
        return () => clearInterval(timer);
    }, [ms]);
    return now;
};

const compare = (column, direction) => (a, b) => {
    const first = a[column];
    const second = b[column];
    // Missing values sort last either way.
    if (first === null || first === undefined) return 1;
    if (second === null || second === undefined) return -1;
    const order = typeof first === 'number' && typeof second === 'number'
        ? first - second
        : String(first).localeCompare(String(second));
    return direction === 'asc' ? order : -order;
};

const uniqueSorted = (pool, field) => [...new Set(pool.map(p => p[field]).filter(Boolean))].sort();

// Filtering, sorting and the Available/Unavailable split for the pool table,
// plus per-player context the table shows (lineup exposure).
export default function usePlayerPool({ pool, lineups, locked, excluded, includeStarted, isPastSlate }) {
    const [filters, setFilters] = useState(() => ({ ...EMPTY_FILTERS, cutoff: defaultKickoffCutoff() }));

    // The kickoff cutoff defaults by today's weekday, which only means
    // something for the live week; a past week starts on all games.
    useEffect(() => {
        setFilters(prev => ({ ...prev, cutoff: isPastSlate ? '' : defaultKickoffCutoff() }));
    }, [isPastSlate]);
    const [sort, setSort] = useState({ column: 'salary', direction: 'desc' });
    const [tab, setTab] = useState('available');
    const now = useNow(60 * 1000);

    const options = useMemo(() => ({
        position: uniqueSorted(pool, 'position'),
        team: uniqueSorted(pool, 'team'),
        opponent: uniqueSorted(pool, 'opponent'),
    }), [pool]);

    // Which lineups (by index) each player is in.
    const exposure = useMemo(() => {
        const byPlayer = {};
        lineups.forEach((lineup, index) => lineup.forEach(({ player }) => {
            (byPlayer[player] = byPlayer[player] || []).push(index);
        }));
        return byPlayer;
    }, [lineups]);

    const unavailableReason = useMemo(() => (player) => {
        const started = !includeStarted && hasKickoffPassed(player.kickoff, now);
        const isExcluded = excluded.includes(player.player);
        if (started && isExcluded) return 'both';
        if (started) return 'started';
        if (isExcluded) return 'excluded';
        return null;
    }, [excluded, includeStarted, now]);

    const filtered = useMemo(() => {
        const search = filters.search.trim().toLowerCase();
        return pool.filter((p) => {
            if (search && !p.player.toLowerCase().includes(search)) return false;
            if (filters.position && p.position !== filters.position) return false;
            if (filters.team && p.team !== filters.team) return false;
            if (filters.opponent && p.opponent !== filters.opponent) return false;
            if (!satisfiesKickoffCutoff(p.kickoff, filters.cutoff)) return false;
            if (filters.quick === 'value' && !(Number(p.value) >= VALUE_PLAY_THRESHOLD)) return false;
            if (filters.quick === 'locked' && !locked.includes(p.player)) return false;
            if (filters.quick === 'excluded' && !excluded.includes(p.player)) return false;
            if (filters.quick === 'lineups' && !exposure[p.player]) return false;
            return true;
        });
    }, [pool, filters, locked, excluded, exposure]);

    const { available, unavailable } = useMemo(() => {
        const byColumn = compare(sort.column, sort.direction);
        return {
            available: filtered.filter(p => !unavailableReason(p)).sort(byColumn),
            unavailable: filtered.filter(p => unavailableReason(p)).sort(byColumn),
        };
    }, [filtered, sort, unavailableReason]);

    const setFilter = (name, value) => {
        setFilters(prev => ({ ...prev, [name]: value }));
        // Excluded players only appear under Unavailable; the others under Available.
        if (name === 'quick' && value) setTab(value === 'excluded' ? 'unavailable' : 'available');
    };

    const toggleSort = column => setSort(prev => (
        prev.column === column
            ? { column, direction: prev.direction === 'asc' ? 'desc' : 'asc' }
            : { column, direction: 'desc' }
    ));

    const hasActiveFilters = Object.keys(EMPTY_FILTERS).some(name => filters[name]);

    return {
        filters, setFilter, clearFilters: () => setFilters(EMPTY_FILTERS), hasActiveFilters,
        options, sort, toggleSort, tab, setTab,
        available, unavailable, rows: tab === 'available' ? available : unavailable,
        exposure, unavailableReason,
    };
}
