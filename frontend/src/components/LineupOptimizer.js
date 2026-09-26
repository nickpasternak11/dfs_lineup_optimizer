import React, { useState, useEffect, useMemo, useCallback } from 'react';
import axios from 'axios';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import './LineupOptimizer.css';

const protocol = window.location.protocol;
export const BASE_HOSTNAME = window.location.hostname;
export const BASE_URL = `${protocol}//${BASE_HOSTNAME}`;
export const BASE_URL_API = `${BASE_URL}:8080`;

const playerColumns = ["position", "player", "proj_fpts", "salary"];
const mainPlayerColumns = ["position", "player", "team", "opponent", "grade", "avg_fpts", "proj_fpts", "salary", "salary_change", "value"];
const sortableColumns = ["avg_fpts", "proj_fpts", "salary", "salary_change", "value"];

const columnLabels = {
    player: "Player",
    position: "Pos",
    team: "Team",
    opponent: "Opp",
    grade: "Grade",
    avg_fpts: "Avg FPTS",
    proj_fpts: "Proj FPTS",
    salary: "Salary",
    salary_change: "Salary Δ",
    value: "Value"
};

const TOTAL_ROSTER_LIMIT = 9;
const SALARY_CAP = 50000;
// NOTE: renamed storage key (v2) because the shape changed from a flat array
// to a map keyed by year-week. Old flat-array data under the v1 key is
// intentionally left alone/ignored rather than migrated, since exclusions
// tied to no particular week can't be safely reassigned to one.
const EXCLUDED_PLAYERS_STORAGE_KEY = 'dfs-lineup-optimizer-excluded-players-v2';

const KICKOFF_CUTOFF_OPTIONS = [
    { label: 'All Games (No Cutoff)', value: '' },
    { label: 'Friday or Later (Hide Thursday)', value: 'friday' },
    { label: 'Sunday or Later (Hide Thu/Fri/Sat)', value: 'sunday' },
    { label: 'Sunday Main Slate (1 PM ET+)', value: 'sunday_main' },
];

const weekKey = (y, w) => `${y || 'unknown'}-${w || 'unknown'}`;

const loadExcludedPlayersMap = () => {
    try {
        const saved = window.localStorage.getItem(EXCLUDED_PLAYERS_STORAGE_KEY);
        const parsed = saved ? JSON.parse(saved) : {};
        return (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) ? parsed : {};
    } catch (error) {
        console.warn('Unable to restore excluded players:', error);
        return {};
    }
};

const formatKickoff = (val) => {
    if (!val) return '';
    const date = new Date(val);
    if (isNaN(date.getTime())) return val;

    return new Intl.DateTimeFormat('en-US', {
        month: 'numeric',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    }).format(date);
};

const formatCompactKickoff = (val) => {
    if (!val) return '';
    const date = new Date(val);
    if (isNaN(date.getTime())) return '';

    const formatted = new Intl.DateTimeFormat('en-US', {
        weekday: 'short',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    }).format(date);

    return formatted.replace(',', '').replace(/ (AM|PM)$/, '$1');
};

const formatCellValue = (key, val) => {
    if (val === null || val === undefined) return '';
    if (key === 'kickoff') return formatKickoff(val);
    if (key === 'salary') return `$${Number(val).toLocaleString()}`;
    if (key === 'salary_change') {
        const num = Number(val);
        return `${num > 0 ? '+' : ''}${num.toLocaleString()}`;
    }
    if (key === 'value') return Number(val).toFixed(2);
    return val;
};

const isHomePlayer = (player) => {
    const homeValue = String(player.home ?? '').toLowerCase();
    return [true, 1, '1', 'true', 'h', 'home'].includes(player.home) ||
        ['1', 'true', 'h', 'home'].includes(homeValue);
};

const formatLineupMatchup = (player) => {
    if (!player.team || !player.opponent) return '';
    return `${isHomePlayer(player) ? 'vs' : '@'} ${player.opponent}`;
};

const formatPoolOpponent = (player) => {
    return `${isHomePlayer(player) ? '' : '@'}${player.opponent || ''}`.trim();
};

const ROSTER_SLOTS = [['QB', 1], ['RB', 2], ['WR', 3], ['TE', 1]];
const FLEX_POSITIONS = ['RB', 'WR', 'TE'];

// Orders a lineup QB, RB, RB, WR, WR, WR, TE, FLEX, DST. Within a position the
// higher projection fills the base slot, so the extra RB/WR/TE becomes FLEX.
const orderLineup = (lineup) => {
    const byPosition = {};
    [...lineup]
        .sort((a, b) => b.proj_fpts - a.proj_fpts)
        .forEach(player => {
            (byPosition[player.position] = byPosition[player.position] || []).push(player);
        });

    const slots = [];
    ROSTER_SLOTS.forEach(([position, count]) => {
        (byPosition[position] || []).splice(0, count)
            .forEach(player => slots.push({ slot: position, player }));
    });
    FLEX_POSITIONS.forEach(position => {
        (byPosition[position] || []).splice(0)
            .forEach(player => slots.push({ slot: 'FLEX', player }));
    });
    (byPosition.DST || []).forEach(player => slots.push({ slot: 'DST', player }));
    return slots;
};

// Lineup structure & salary cap validator
const canIncludePlayer = (playerToInclude, currentIncludedNames, projectionsList) => {
    if (!playerToInclude) return { allowed: false, reason: "Player not found." };

    if (currentIncludedNames.includes(playerToInclude.player)) {
        return { allowed: true };
    }

    if (currentIncludedNames.length >= TOTAL_ROSTER_LIMIT) {
        return { allowed: false, reason: "Lineup is full (9/9 players selected)." };
    }

    const currentIncluded = projectionsList.filter(p => currentIncludedNames.includes(p.player));

    const currentSalaryTotal = currentIncluded.reduce((sum, p) => sum + (p.salary || 0), 0);
    const newSalary = playerToInclude.salary || 0;
    if (currentSalaryTotal + newSalary > SALARY_CAP) {
        const remaining = SALARY_CAP - currentSalaryTotal;
        return {
            allowed: false,
            reason: `Exceeds salary cap. Remaining budget: $${remaining.toLocaleString()} (Player costs $${newSalary.toLocaleString()}).`
        };
    }

    const counts = { QB: 0, RB: 0, WR: 0, TE: 0, DST: 0 };
    currentIncluded.forEach(p => {
        if (counts[p.position] !== undefined) counts[p.position]++;
    });

    const targetPos = playerToInclude.position;

    if (targetPos === 'QB' && counts.QB >= 1) {
        return { allowed: false, reason: "Max 1 QB allowed." };
    }
    if (targetPos === 'DST' && counts.DST >= 1) {
        return { allowed: false, reason: "Max 1 DST allowed." };
    }

    const flexUsed = Math.max(0, counts.RB - 2) + Math.max(0, counts.WR - 3) + Math.max(0, counts.TE - 1);

    if (targetPos === 'RB') {
        if (counts.RB >= 2 && flexUsed >= 1) return { allowed: false, reason: "Max 3 RBs allowed (including FLEX)." };
    } else if (targetPos === 'WR') {
        if (counts.WR >= 3 && flexUsed >= 1) return { allowed: false, reason: "Max 4 WRs allowed (including FLEX)." };
    } else if (targetPos === 'TE') {
        if (counts.TE >= 1 && flexUsed >= 1) return { allowed: false, reason: "Max 2 TEs allowed (including FLEX)." };
    }

    return { allowed: true };
};

const getCellStyle = (key, val) => {
    if (key === 'salary_change' && val !== null && val !== undefined) {
        const num = Number(val);
        if (num > 0) return { color: '#28a745', fontWeight: '600' };
        if (num < 0) return { color: '#dc3545', fontWeight: '600' };
    }
    return {};
};

// Renders the salary delta with a directional arrow so the sign doesn't
// depend on color alone (helps colorblind users and quick scanning).
const renderSalaryChange = (val) => {
    if (val === null || val === undefined) return '';
    const num = Number(val);
    if (num > 0) return <span className="salary-delta salary-delta-up">▲ {num.toLocaleString()}</span>;
    if (num < 0) return <span className="salary-delta salary-delta-down">▼ {Math.abs(num).toLocaleString()}</span>;
    return <span className="salary-delta salary-delta-flat">—</span>;
};

const getGradeClassName = (grade) => {
    const normalizedGrade = String(grade || '').trim().toUpperCase();
    if (normalizedGrade.startsWith('A')) return 'grade-a';
    if (normalizedGrade.startsWith('B')) return 'grade-b';
    if (normalizedGrade.startsWith('C')) return 'grade-c';
    if (normalizedGrade.startsWith('F')) return 'grade-f';
    return 'grade-d';
};

const getDefenseClassName = (defenseRank) => {
    const rank = Number(defenseRank);
    if (!Number.isFinite(rank)) return '';
    if (rank <= 10) return 'opponent-top-defense';
    if (rank >= 23) return 'opponent-bottom-defense';
    return '';
};

const getInjuryStatusLabel = (player) => {
    const status = String(player.injury_status || '').trim().toLowerCase();
    const labels = {
        questionable: 'Q',
        ir: 'IR',
        out: 'O',
        pup: 'PUP',
        suspended: 'S',
        doubtful: 'D',
    };

    return labels[status] || '';
};

const hasKickoffPassed = (kickoffStr) => {
    if (!kickoffStr) return false;
    const kickoffDate = new Date(kickoffStr);
    return !isNaN(kickoffDate.getTime()) && kickoffDate <= new Date();
};

function LineupOptimizer() {
    const [year, setYear] = useState('');
    const [week, setWeek] = useState('');
    const [currentYear, setCurrentYear] = useState('');
    const [currentWeek, setCurrentWeek] = useState('');
    const [stackQBCount, setStackQBCount] = useState(0);
    const [avoidTEFlex, setAvoidTEFlex] = useState(false);
    const [includeStartedPlayers, setIncludeStartedPlayers] = useState(false);
    const [excludedPlayersMap, setExcludedPlayersMap] = useState(loadExcludedPlayersMap);
    const [includedPlayers, setIncludedPlayers] = useState([]);
    const [lineups, setLineups] = useState([]);
    const [projections, setProjections] = useState([]);
    const [playerSearch, setPlayerSearch] = useState('');
    const [positionFilter, setPositionFilter] = useState('');
    const [teamFilter, setTeamFilter] = useState('');
    const [opponentFilter, setOpponentFilter] = useState('');
    const [kickoffCutoff, setKickoffCutoff] = useState('');
    const [quickFilter, setQuickFilter] = useState(null); // 'value' | 'locked' | 'excluded' | null
    const [loading, setLoading] = useState(false);
    const [initialLoading, setInitialLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('lineup1');
    const [playerPoolTab, setPlayerPoolTab] = useState('available');

    // Sorting state
    const [sortColumn, setSortColumn] = useState('salary');
    const [sortDirection, setSortDirection] = useState('desc');

    // Excluded players are scoped to the currently selected year/week so an
    // exclusion made for one slate doesn't silently carry over to another.
    const excludedPlayers = useMemo(
        () => excludedPlayersMap[weekKey(year, week)] || [],
        [excludedPlayersMap, year, week]
    );

    // Dynamically calculate smart default cutoff based on current day of the week
    const getDefaultCutoff = () => {
        const now = new Date();
        const day = now.getDay(); // 0 = Sun, 1 = Mon, ..., 5 = Fri, 6 = Sat

        // If it's Friday or Saturday, default to hiding Thursday games
        if (day === 5 || day === 6) {
            return 'friday';
        }
        // If it's Sunday after Thursday/Friday games, default to Sunday games
        if (day === 0) {
            return 'sunday';
        }
        return '';
    };

    const getFilterOptions = useCallback((field) => {
        return [...new Set(
            projections.map(projection => projection[field]).filter(Boolean)
        )].sort();
    }, [projections]);

    const positionOptions = useMemo(() => getFilterOptions('position'), [getFilterOptions]);
    const teamOptions = useMemo(() => getFilterOptions('team'), [getFilterOptions]);
    const opponentOptions = useMemo(() => getFilterOptions('opponent'), [getFilterOptions]);

    // Helper to evaluate if a kickoff passes the selected cutoff filter
    const satisfiesKickoffCutoff = (kickoffStr, cutoffKey) => {
        if (!cutoffKey || !kickoffStr) return true;
        const kDate = new Date(kickoffStr);
        if (isNaN(kDate.getTime())) return true;

        const yearNum = kDate.getFullYear();
        const monthNum = kDate.getMonth();
        const dateNum = kDate.getDate();

        if (cutoffKey === 'friday') {
            // Include games starting Friday (day index 5) or later in the week
            return kDate.getDay() >= 5 || kDate.getDay() === 0 || kDate.getDay() === 1;
        }
        if (cutoffKey === 'sunday') {
            // Include Sunday (0) or Monday (1) games
            return kDate.getDay() === 0 || kDate.getDay() === 1;
        }
        if (cutoffKey === 'sunday_main') {
            // Include Sunday games starting at or after 1:00 PM ET
            if (kDate.getDay() !== 0) return false;
            const sundayNoon = new Date(yearNum, monthNum, dateNum, 13, 0, 0);
            return kDate >= sundayNoon;
        }
        return true;
    };

    const filteredProjections = useMemo(() => {
        return projections.filter(projection => {
            if (!projection.player?.toLowerCase().includes(playerSearch.toLowerCase())) return false;
            if (positionFilter && projection.position !== positionFilter) return false;
            if (teamFilter && projection.team !== teamFilter) return false;
            if (opponentFilter && projection.opponent !== opponentFilter) return false;
            if (!satisfiesKickoffCutoff(projection.kickoff, kickoffCutoff)) return false;
            if (quickFilter === 'value' && !(Number(projection.value) >= 2.5)) return false;
            if (quickFilter === 'locked' && !includedPlayers.includes(projection.player)) return false;
            if (quickFilter === 'excluded' && !excludedPlayers.includes(projection.player)) return false;
            return true;
        });
    }, [projections, playerSearch, positionFilter, teamFilter, opponentFilter, kickoffCutoff, quickFilter, includedPlayers, excludedPlayers]);

    const sortPlayers = useCallback((players) => [...players].sort((firstPlayer, secondPlayer) => {
        if (!sortColumn) return 0;

        let firstValue = firstPlayer[sortColumn];
        let secondValue = secondPlayer[sortColumn];

        if (firstValue === null || firstValue === undefined) return 1;
        if (secondValue === null || secondValue === undefined) return -1;

        if (typeof firstValue === 'number' && typeof secondValue === 'number') {
            return sortDirection === 'asc' ? firstValue - secondValue : secondValue - firstValue;
        }

        firstValue = String(firstValue).toUpperCase();
        secondValue = String(secondValue).toUpperCase();

        if (firstValue < secondValue) return sortDirection === 'asc' ? -1 : 1;
        if (firstValue > secondValue) return sortDirection === 'asc' ? 1 : -1;
        return 0;
    }), [sortColumn, sortDirection]);

    // A player is unavailable either because their game already kicked off,
    // or because the user manually excluded them. These are surfaced as
    // distinct reasons in the UI (see getUnavailabilityReason) even though
    // both land in the same "Unavailable" tab.
    const isPlayerUnavailable = useCallback((player) => {
        if (excludedPlayers.includes(player.player)) return true;
        return !includeStartedPlayers && hasKickoffPassed(player.kickoff);
    }, [excludedPlayers, includeStartedPlayers]);

    const getUnavailabilityReason = useCallback((player) => {
        const started = !includeStartedPlayers && hasKickoffPassed(player.kickoff);
        const excluded = excludedPlayers.includes(player.player);
        if (started && excluded) return 'both';
        if (started) return 'started';
        if (excluded) return 'excluded';
        return null;
    }, [excludedPlayers, includeStartedPlayers]);

    const availableProjections = useMemo(() => (
        sortPlayers(filteredProjections.filter(player => !isPlayerUnavailable(player)))
    ), [filteredProjections, isPlayerUnavailable, sortPlayers]);

    const unavailableProjections = useMemo(() => (
        sortPlayers(filteredProjections.filter(isPlayerUnavailable))
    ), [filteredProjections, isPlayerUnavailable, sortPlayers]);

    const displayedProjections = playerPoolTab === 'available'
        ? availableProjections
        : unavailableProjections;

    const handleSort = (col) => {
        if (!sortableColumns.includes(col)) return;

        if (sortColumn === col) {
            setSortDirection(prev => (prev === 'asc' ? 'desc' : 'asc'));
        } else {
            setSortColumn(col);
            setSortDirection(col === 'rank' ? 'asc' : 'desc');
        }
    };

    const handleSortKeyDown = (event, col) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            handleSort(col);
        }
    };

    const toggleExclude = (playerName) => {
        const key = weekKey(year, week);
        const currentList = excludedPlayersMap[key] || [];
        const isCurrentlyExcluded = currentList.includes(playerName);
        const nextList = isCurrentlyExcluded
            ? currentList.filter(player => player !== playerName)
            : [...currentList, playerName];
        const nextIncludedPlayers = isCurrentlyExcluded
            ? includedPlayers
            : includedPlayers.filter(player => player !== playerName);

        setExcludedPlayersMap(prev => ({ ...prev, [key]: nextList }));
        setIncludedPlayers(nextIncludedPlayers);

        const appearsInSuggestedLineup = lineups.some(lineup => (
            lineup.some(player => player.player === playerName)
        ));

        if (!isCurrentlyExcluded && appearsInSuggestedLineup) {
            optimizeLineups(year, week, nextList, nextIncludedPlayers);
        }
    };

    const toggleInclude = (playerTarget) => {
        const playerName = typeof playerTarget === 'string' ? playerTarget : playerTarget.player;

        if (includedPlayers.includes(playerName)) {
            setIncludedPlayers(prev => prev.filter(p => p !== playerName));
            return;
        }

        const targetObj = typeof playerTarget === 'object'
            ? playerTarget
            : projections.find(p => p.player === playerName);

        const check = canIncludePlayer(targetObj, includedPlayers, projections);
        if (!check.allowed) {
            toast.warning(check.reason);
            return;
        }

        const nextIncludedPlayers = [...includedPlayers, playerName];
        const key = weekKey(year, week);
        const currentList = excludedPlayersMap[key] || [];
        const nextExcludedList = currentList.filter(player => player !== playerName);

        setIncludedPlayers(nextIncludedPlayers);
        setExcludedPlayersMap(prev => ({ ...prev, [key]: nextExcludedList }));

        const appearsInSuggestedLineup = lineups.some(lineup => (
            lineup.some(player => player.player === playerName)
        ));

        if (!appearsInSuggestedLineup) {
            optimizeLineups(year, week, nextExcludedList, nextIncludedPlayers);
        }
    };

    const renderActionButtons = (player, isUnavailable = false) => {
        const playerObj = typeof player === 'string'
            ? projections.find(p => p.player === player)
            : player;

        const playerName = playerObj ? playerObj.player : player;
        const isExcluded = excludedPlayers.includes(playerName);
        const isIncluded = includedPlayers.includes(playerName);
        const check = canIncludePlayer(playerObj, includedPlayers, projections);
        const canBeIncluded = isIncluded || check.allowed;

        if (isUnavailable) {
            if (!isExcluded) return <span className="player-unavailable-label">Played</span>;

            return (
                <button
                    type="button"
                    className="action-button text-success"
                    onClick={() => toggleExclude(playerName)}
                    title={`Restore ${playerName} to available players`}
                    aria-label={`Restore ${playerName} to available players`}
                >
                    <span role="img" aria-label="Restore">↩️</span>
                </button>
            );
        }

        // Buttons stay clickable even when the action isn't currently allowed
        // (e.g. lineup full, over salary cap) so the reason surfaces as a
        // toast on tap — a native `disabled` button never fires a touch
        // event, so its `title` tooltip is invisible on mobile.
        return (
            <span className="player-actions">
                {!isIncluded && (
                    <button
                        type="button"
                        className={`action-button text-danger ${!canBeIncluded ? 'is-unavailable' : ''}`}
                        onClick={() => {
                            if (!canBeIncluded) { toast.warning(check.reason); return; }
                            toggleExclude(playerName);
                        }}
                        title={!canBeIncluded ? check.reason : `Exclude ${playerName}`}
                        aria-label={`Exclude ${playerName}`}
                    >
                        <span role="img" aria-label="Exclude">🚫</span>
                    </button>
                )}
                <button
                    type="button"
                    className={`action-button text-success ${!isIncluded && !canBeIncluded ? 'is-unavailable' : ''}`}
                    onClick={() => {
                        if (!isIncluded && !canBeIncluded) { toast.warning(check.reason); return; }
                        toggleInclude(playerObj || playerName);
                    }}
                    title={isIncluded ? `Unlock ${playerName}` : (!canBeIncluded ? check.reason : `Include/Lock ${playerName}`)}
                    aria-label={isIncluded ? `Unlock ${playerName}` : `Include or lock ${playerName}`}
                >
                    <span role="img" aria-label={isIncluded ? "Locked" : "Include"}>
                        {isIncluded ? '🔒' : '🔓'}
                    </span>
                </button>
            </span>
        );
    };

    const fetchProjections = async (selectedYear = year, selectedWeek = week) => {
        const response = await axios.post(`${BASE_URL_API}/projections`, {
            year: selectedYear ? parseInt(selectedYear) : null,
            week: selectedWeek ? parseInt(selectedWeek) : null,
        });
        setProjections(response.data);
    };

    const optimizeLineups = async (
        selectedYear = year,
        selectedWeek = week,
        selectedExcludedPlayers = excludedPlayers,
        selectedIncludedPlayers = includedPlayers
    ) => {
        setLoading(true);
        try {
            const data = {
                year: selectedYear ? parseInt(selectedYear) : null,
                week: selectedWeek ? parseInt(selectedWeek) : null,
                stack_qb_count: stackQBCount,
                avoid_te_flex: avoidTEFlex,
                include_started_players: includeStartedPlayers,
                excluded_players: selectedExcludedPlayers,
                included_players: selectedIncludedPlayers
            };
            await fetchProjections(selectedYear, selectedWeek);
            const response = await axios.post(`${BASE_URL_API}/optimize`, data);
            setLineups(response.data);
            if (response.data.length > 0) {
                toast.success('Lineup optimization successful!');
            }
        } catch (error) {
            console.error('Error:', error);
            const errorMsg = error.response?.data?.detail || 'Unable to load projections or optimize the lineup. Please try again.';
            toast.error(`Error: ${errorMsg}`);
        } finally {
            setLoading(false);
            setInitialLoading(false);
        }
    };

    const fetchCurrentPeriod = async () => {
        const yearResponse = await axios.get(`${BASE_URL_API}/projections/current_year`);
        const weekResponse = await axios.get(`${BASE_URL_API}/projections/current_week`);
        const current_year = String(yearResponse.data);
        const current_week = String(weekResponse.data);
        setYear(current_year);
        setWeek(current_week);
        setCurrentYear(current_year);
        setCurrentWeek(current_week);
        setKickoffCutoff(getDefaultCutoff());
        optimizeLineups(currentYear, currentWeek);
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        optimizeLineups();
    };

    const hasActivePlayerFilters = Boolean(
        playerSearch || positionFilter || teamFilter || opponentFilter || kickoffCutoff || quickFilter
    );

    const clearPlayerFilters = () => {
        setPlayerSearch('');
        setPositionFilter('');
        setTeamFilter('');
        setOpponentFilter('');
        setKickoffCutoff('');
        setQuickFilter(null);
    };

    useEffect(() => {
        try {
            window.localStorage.setItem(EXCLUDED_PLAYERS_STORAGE_KEY, JSON.stringify(excludedPlayersMap));
        } catch (error) {
            console.warn('Unable to persist excluded players:', error);
        }
    }, [excludedPlayersMap]);

    useEffect(() => {
        fetchCurrentPeriod().catch((error) => {
            console.error('Error loading current year and week:', error);
            toast.error('Unable to load the current year and week. Please try again.');
            setInitialLoading(false);
        });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const renderQuickFilterChip = (key, label) => (
        <button
            type="button"
            className={`quick-filter-chip ${quickFilter === key ? 'active' : ''}`}
            onClick={() => setQuickFilter(prev => (prev === key ? null : key))}
            aria-pressed={quickFilter === key}
        >
            {label}
        </button>
    );

    const renderSortableHeader = (col) => {
        const isSortable = sortableColumns.includes(col);
        const isSorted = sortColumn === col;
        const ariaSort = !isSortable ? undefined : (isSorted ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none');

        return (
            <th
                key={col}
                onClick={() => isSortable && handleSort(col)}
                onKeyDown={isSortable ? (e) => handleSortKeyDown(e, col) : undefined}
                tabIndex={isSortable ? 0 : undefined}
                role={isSortable ? 'columnheader button' : undefined}
                aria-sort={ariaSort}
                style={{ cursor: isSortable ? 'pointer' : 'default', userSelect: 'none' }}
                title={isSortable ? `Sort by ${columnLabels[col] || col}` : ''}
            >
                {columnLabels[col] || col}
                {isSortable && (
                    <span style={{ marginLeft: '4px', opacity: isSorted ? 1 : 0.4 }} aria-hidden="true">
                        {isSorted ? (sortDirection === 'asc' ? '▲' : '▼') : '↕'}
                    </span>
                )}
            </th>
        );
    };

    const renderProjectionTable = (players, emptyMessage, isUnavailable = false, isLoading = false) => (
        <div className="player-table-wrap">
            <table className="table table-striped player-pool-table">
                <thead>
                    <tr>
                        {mainPlayerColumns.map(renderSortableHeader)}
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {isLoading ? (
                        <tr>
                            <td className="empty-player-state" colSpan={mainPlayerColumns.length + 1}>Loading players…</td>
                        </tr>
                    ) : players.length === 0 ? (
                        <tr>
                            <td className="empty-player-state" colSpan={mainPlayerColumns.length + 1}>{emptyMessage}</td>
                        </tr>
                    ) : players.map((player, playerIndex) => {
                        const isIncluded = includedPlayers.includes(player.player);
                        const reason = isUnavailable ? getUnavailabilityReason(player) : null;
                        return (
                            <tr
                                key={`${player.player}-${playerIndex}`}
                                className={`${isIncluded ? 'row-player-locked' : ''} ${isUnavailable ? 'row-player-unavailable' : ''}`.trim()}
                            >
                                {mainPlayerColumns.map(col => (
                                    <td key={col} style={getCellStyle(col, player[col])}>
                                        {col === 'player' ? (
                                            <span className="pool-player-name">
                                                {player.player}
                                                {getInjuryStatusLabel(player) && (
                                                    <span className="injury-status-label">{getInjuryStatusLabel(player)}</span>
                                                )}
                                                {reason && (
                                                    <span className={`unavailable-reason-tag reason-${reason}`}>
                                                        {reason === 'started' ? 'Started' : reason === 'excluded' ? 'Excluded' : 'Started · Excluded'}
                                                    </span>
                                                )}
                                            </span>
                                        ) : col === 'opponent' ? (
                                            <div className={`pool-opponent-cell ${getDefenseClassName(
                                                projections.find(projection => (
                                                    projection.position === 'DST' && projection.team === player.opponent
                                                ))?.rank
                                            )}`}>
                                                <span>{formatPoolOpponent(player)}</span>
                                                <small>{formatCompactKickoff(player.kickoff)}</small>
                                            </div>
                                        ) : col === 'grade' ? (
                                            <span className={`grade-badge ${getGradeClassName(player[col])}`}>
                                                {formatCellValue(col, player[col])}
                                            </span>
                                        ) : col === 'salary_change' ? (
                                            renderSalaryChange(player[col])
                                        ) : formatCellValue(col, player[col])}
                                    </td>
                                ))}
                                <td>{renderActionButtons(player, isUnavailable)}</td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );

    return (
        <div className="container">
            <ToastContainer theme="dark" />
            <header className="page-header">
                <img className="brand-logo" src={`${process.env.PUBLIC_URL}/favicon-192x192.png`} alt="" />
                <div>
                    <h1>DFS Lineup Optimizer</h1>
                </div>
            </header>

            <div className="optimizer-layout">
                <main className="player-pool-main">
                    <div className="section-heading">
                        <div>
                            <p className="eyebrow">Player pool</p>
                            <h2>{playerPoolTab === 'available' ? 'Available players' : 'Unavailable players'}</h2>
                        </div>
                        <div className="player-count-badges">
                            <span className="result-count">Available {availableProjections.length}</span>
                            <span className="result-count result-count-unavailable">Unavailable {unavailableProjections.length}</span>
                        </div>
                    </div>
                    <div className="player-pool-tabs" role="tablist" aria-label="Player pool status">
                        <button
                            type="button"
                            role="tab"
                            aria-selected={playerPoolTab === 'available'}
                            className={playerPoolTab === 'available' ? 'active' : ''}
                            onClick={() => setPlayerPoolTab('available')}
                        >
                            Available
                        </button>
                        <button
                            type="button"
                            role="tab"
                            aria-selected={playerPoolTab === 'unavailable'}
                            className={playerPoolTab === 'unavailable' ? 'active' : ''}
                            onClick={() => setPlayerPoolTab('unavailable')}
                        >
                            Unavailable
                        </button>
                    </div>
                    <div className="player-filters">
                        <div className="quick-filters">
                            <span className="quick-filters-label">Quick filters</span>
                            {renderQuickFilterChip('value', 'Value plays 2.5x+')}
                            {renderQuickFilterChip('locked', 'Locked only')}
                            {renderQuickFilterChip('excluded', 'Excluded only')}
                        </div>
                        <div className="primary-filters">
                            <input
                                type="search"
                                id="player-search"
                                className="form-control form-control-sm"
                                value={playerSearch}
                                onChange={(e) => setPlayerSearch(e.target.value)}
                                placeholder="Search players"
                            />
                            <select
                                className="form-select form-select-sm"
                                value={kickoffCutoff}
                                onChange={(e) => setKickoffCutoff(e.target.value)}
                                aria-label="Filter by Kickoff Slate"
                            >
                                {KICKOFF_CUTOFF_OPTIONS.map(opt => (
                                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                                ))}
                            </select>
                        </div>
                        <div className="secondary-filters">
                            {[
                                ['Position', positionFilter, setPositionFilter, positionOptions],
                                ['Team', teamFilter, setTeamFilter, teamOptions],
                                ['Opponent', opponentFilter, setOpponentFilter, opponentOptions],
                            ].map(([label, value, setter, options]) => (
                                <select key={label} className="form-select form-select-sm" value={value} onChange={(e) => setter(e.target.value)} aria-label={`Filter by ${label}`}>
                                    <option value="">All {label}s</option>
                                    {options.map(option => <option key={option} value={option}>{option}</option>)}
                                </select>
                            ))}
                        </div>
                        {hasActivePlayerFilters && (
                            <div className="active-filters-row">
                                <span className="active-filters-count">
                                    {displayedProjections.length} of {playerPoolTab === 'available' ? availableProjections.length + '' : unavailableProjections.length} shown
                                </span>
                                <button
                                    type="button"
                                    className="clear-filters-button"
                                    onClick={clearPlayerFilters}
                                >
                                    <span className="clear-filters-icon" aria-hidden="true">×</span>
                                    Clear filters
                                </button>
                            </div>
                        )}
                    </div>
                    {renderProjectionTable(
                        displayedProjections,
                        playerPoolTab === 'available' ? 'No available players match these filters.' : 'No unavailable players match these filters.',
                        playerPoolTab === 'unavailable',
                        initialLoading
                    )}
                </main>

                <aside className="right-sidebar">
                    <div className="side-panel">
                        <div id="optimizer-settings">
                            <div className="section-heading sidebar-results-heading">
                                <div>
                                    <p className="eyebrow">Optimization results</p>
                                    <h2>Suggested lineups</h2>
                                </div>
                            </div>
                            <form onSubmit={handleSubmit} className="optimizer-controls">
                                <div className="filter-grid">
                                    <div className="form-group">
                                        <label htmlFor="year">Year</label>
                                        <input
                                            type="number"
                                            id="year"
                                            className="form-control form-control-sm"
                                            value={year}
                                            onChange={(e) => setYear(e.target.value)}
                                            min="2018"
                                            max={currentYear}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label htmlFor="week">Week</label>
                                        <input
                                            type="number"
                                            id="week"
                                            className="form-control form-control-sm"
                                            value={week}
                                            onChange={(e) => setWeek(e.target.value)}
                                            min="1"
                                            max="18"
                                        />
                                    </div>
                                </div>
                                <div className="form-check-stack">
                                    <input
                                        type="checkbox"
                                        id="stack_qb_one"
                                        className="form-check-input optimizer-toggle"
                                        checked={stackQBCount === 1}
                                        onChange={() => setStackQBCount(current => current === 1 ? 0 : 1)}
                                        role="switch"
                                        aria-checked={stackQBCount === 1}
                                    />
                                    <label className="form-check-label" htmlFor="stack_qb_one">
                                        Stack QB with 1 WR/TE
                                    </label>
                                </div>
                                <div className="form-check-stack">
                                    <input
                                        type="checkbox"
                                        id="stack_qb_two"
                                        className="form-check-input optimizer-toggle"
                                        checked={stackQBCount === 2}
                                        onChange={() => setStackQBCount(current => current === 2 ? 0 : 2)}
                                        role="switch"
                                        aria-checked={stackQBCount === 2}
                                    />
                                    <label className="form-check-label" htmlFor="stack_qb_two">
                                        Stack QB with 2 WR/TE
                                    </label>
                                </div>
                                <div className="form-check-stack">
                                    <input
                                        type="checkbox"
                                        id="avoid_te_flex"
                                        className="form-check-input optimizer-toggle"
                                        checked={avoidTEFlex}
                                        onChange={(e) => setAvoidTEFlex(e.target.checked)}
                                        role="switch"
                                        aria-checked={avoidTEFlex}
                                    />
                                    <label className="form-check-label" htmlFor="avoid_te_flex">
                                        Avoid TE in FLEX
                                    </label>
                                </div>
                                <div className="form-check-stack">
                                    <input
                                        type="checkbox"
                                        id="include_started_players"
                                        className="form-check-input optimizer-toggle"
                                        checked={includeStartedPlayers}
                                        onChange={(e) => setIncludeStartedPlayers(e.target.checked)}
                                        role="switch"
                                        aria-checked={includeStartedPlayers}
                                    />
                                    <label className="form-check-label" htmlFor="include_started_players">
                                        Include players whose games have started
                                    </label>
                                </div>
                                <button type="submit" className="btn btn-primary optimize-button">Optimize</button>
                            </form>

                        </div>
                    </div>

                    <div className="results-panel">
                        {loading && <div className="results-loading">Optimizing...</div>}
                        {lineups.length > 0 && (
                            <>
                                <ul className="nav nav-tabs lineup-tabs" id="lineupTabs" role="tablist">
                                    {lineups.map((_, index) => (
                                        <li key={index} className="nav-item" role="presentation">
                                            <button className={`nav-link ${activeTab === `lineup${index + 1}` ? 'active' : ''}`} onClick={() => setActiveTab(`lineup${index + 1}`)}>
                                                Lineup {index + 1}
                                            </button>
                                        </li>
                                    ))}
                                </ul>
                                <div className="tab-content">
                                    {lineups.map((lineup, index) => (
                                        <div key={index} className={`tab-pane fade ${activeTab === `lineup${index + 1}` ? 'show active' : ''}`}>
                                            <div className="lineup-table-wrap">
                                                <table className="table table-striped">
                                                    <thead>
                                                        <tr>
                                                            {playerColumns.map(col => (
                                                                <th key={col}>{columnLabels[col] || col}</th>
                                                            ))}
                                                            <th>Actions</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {orderLineup(lineup).map(({ slot, player }, playerIndex) => (
                                                            <tr
                                                                key={`${player.player}-${playerIndex}`}
                                                                className={includedPlayers.includes(player.player) ? 'row-player-locked' : ''}
                                                            >
                                                                {playerColumns.map(col => (
                                                                    <td key={col} style={getCellStyle(col, player[col])}>
                                                                        {col === 'position' ? slot : col === 'player' ? (
                                                                            <div className="lineup-player-cell">
                                                                                <strong>
                                                                                    {player.player}
                                                                                    {getInjuryStatusLabel(player) && (
                                                                                        <span className="injury-status-label">{getInjuryStatusLabel(player)}</span>
                                                                                    )}
                                                                                </strong>
                                                                                <span>{player.team} {formatLineupMatchup(player)}</span>
                                                                            </div>
                                                                        ) : formatCellValue(col, player[col])}
                                                                    </td>
                                                                ))}
                                                                <td>{renderActionButtons(player)}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                            <div className="lineup-summary">
                                                <span>{lineup.reduce((sum, player) => sum + player.proj_fpts, 0).toFixed(2)} FPTS</span>
                                                <span>${lineup.reduce((sum, player) => sum + player.salary, 0).toLocaleString()}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </>
                        )}
                    </div>
                </aside>
            </div>
        </div>
    );
}

export default LineupOptimizer;
