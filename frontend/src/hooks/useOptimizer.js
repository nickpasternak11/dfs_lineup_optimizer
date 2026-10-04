import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'react-toastify';
import { errorMessage, fetchCurrentSlate, fetchLineups, fetchProjections } from '../api/client';
import { canLockPlayer } from '../lib/rosterRules';
import { loadExcludedPlayers, saveExcludedPlayers, slateKey } from '../lib/storage';

const DEFAULT_SETTINGS = { stackQbCount: 0, avoidTeFlex: false, includeStarted: false };

// Runs `load` whenever `deps` change, keeping only the newest response: a
// slow reply to an older request never overwrites a newer one.
const useLatest = (load, deps, { onData, onError, onSettled }) => {
    const latest = useRef(0);
    useEffect(() => {
        const request = load && load();
        if (!request) return;
        const id = ++latest.current;
        request
            .then(data => { if (id === latest.current) onData(data); })
            .catch(error => { if (id === latest.current) onError(error); })
            .finally(() => { if (id === latest.current) onSettled(); });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, deps);
};

// The slate, optimizer settings, locks and exclusions, plus the player pool
// and lineups they produce. Any change re-runs the optimizer.
export default function useOptimizer() {
    const [slate, setSlate] = useState({ year: '', week: '' });
    const [current, setCurrent] = useState({ year: '', week: '' });
    const [settings, setSettings] = useState(DEFAULT_SETTINGS);
    const [excludedMap, setExcludedMap] = useState(loadExcludedPlayers);
    const [locked, setLocked] = useState([]);
    const [pool, setPool] = useState([]);
    const [lineups, setLineups] = useState([]);
    const [lineupError, setLineupError] = useState(null);
    const [loadingPool, setLoadingPool] = useState(true);
    const [optimizing, setOptimizing] = useState(false);
    const [refreshCount, setRefreshCount] = useState(0);

    const key = slateKey(slate.year, slate.week);
    const excluded = useMemo(() => excludedMap[key] || [], [excludedMap, key]);

    useEffect(() => {
        fetchCurrentSlate()
            .then((period) => {
                setCurrent(period);
                setSlate(period);
            })
            .catch(() => {
                setLoadingPool(false);
                toast.error('Unable to reach the API to load the current week.');
            });
    }, []);

    useEffect(() => {
        saveExcludedPlayers(excludedMap);
    }, [excludedMap]);

    useLatest(
        () => {
            if (!slate.year || !slate.week) return null;
            setLoadingPool(true);
            return fetchProjections(slate.year, slate.week);
        },
        [slate.year, slate.week, refreshCount],
        {
            onData: setPool,
            onError: (error) => {
                setPool([]);
                toast.error(errorMessage(error, 'Unable to load the player pool.'));
            },
            onSettled: () => setLoadingPool(false),
        },
    );

    useLatest(
        () => {
            if (!slate.year || !slate.week) return null;
            setOptimizing(true);
            return fetchLineups({ ...slate, ...settings, excluded, locked });
        },
        [slate.year, slate.week, settings, excluded, locked, refreshCount],
        {
            onData: (data) => {
                setLineups(data);
                setLineupError(null);
            },
            onError: (error) => {
                setLineups([]);
                setLineupError(errorMessage(error, 'Unable to optimize lineups. Please try again.'));
            },
            onSettled: () => setOptimizing(false),
        },
    );

    // Locks are names from one week's pool, so they don't carry over.
    const changeSlate = useCallback((year, week) => {
        setSlate({ year: String(year), week: String(week) });
        setLocked([]);
    }, []);

    const updateSettings = useCallback(patch => setSettings(prev => ({ ...prev, ...patch })), []);

    const refresh = useCallback(() => setRefreshCount(count => count + 1), []);

    const setExcludedForSlate = useCallback(
        update => setExcludedMap(prev => ({ ...prev, [key]: update(prev[key] || []) })),
        [key],
    );

    const toggleExclude = useCallback((name) => {
        setExcludedForSlate(list => (list.includes(name) ? list.filter(n => n !== name) : [...list, name]));
        setLocked(list => list.filter(n => n !== name));
    }, [setExcludedForSlate]);

    const toggleLock = useCallback((player) => {
        if (locked.includes(player.player)) {
            setLocked(locked.filter(n => n !== player.player));
            return;
        }
        const check = canLockPlayer(player, locked, pool);
        if (!check.allowed) {
            toast.warning(check.reason);
            return;
        }
        setLocked([...locked, player.player]);
        setExcludedForSlate(list => list.filter(n => n !== player.player));
    }, [locked, pool, setExcludedForSlate]);

    const clearLocks = useCallback(() => setLocked([]), []);

    return {
        slate, current, settings, pool, lineups, lineupError, locked, excluded,
        loadingPool, optimizing,
        changeSlate, updateSettings, refresh, toggleExclude, toggleLock, clearLocks,
    };
}
