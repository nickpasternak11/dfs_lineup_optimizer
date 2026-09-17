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

const playerColumns = ["player", "position", "proj_fpts", "salary"];
const mainPlayerColumns = ["player", "position", "team", "opponent", "grade", "avg_fpts", "proj_fpts", "salary", "salary_change", "value"];
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
const EXCLUDED_PLAYERS_STORAGE_KEY = 'dfs-lineup-optimizer-excluded-players';

const KICKOFF_CUTOFF_OPTIONS = [
    { label: 'All Games (No Cutoff)', value: '' },
    { label: 'Friday or Later (Hide Thursday)', value: 'friday' },
    { label: 'Sunday or Later (Hide Thu/Fri/Sat)', value: 'sunday' },
    { label: 'Sunday Main Slate (1 PM ET+)', value: 'sunday_main' },
];

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

const formatLineupMatchup = (player) => {
    if (!player.team || !player.opponent) return '';

    const homeValue = String(player.home ?? '').toLowerCase();
    const isHome = [true, 1, '1', 'true', 'h', 'home'].includes(player.home) ||
        ['1', 'true', 'h', 'home'].includes(homeValue);
    return `${isHome ? 'vs' : '@'} ${player.opponent}`;
};

const formatPoolOpponent = (player) => {
    const homeValue = String(player.home ?? '').toLowerCase();
    const isHome = [true, 1, '1', 'true', 'h', 'home'].includes(player.home) ||
        ['1', 'true', 'h', 'home'].includes(homeValue);
    return `${isHome ? '' : '@'}${player.opponent || ''}`.trim();
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

const getGradeClassName = (grade) => {
    const normalizedGrade = String(grade || '').trim().toUpperCase();
    if (normalizedGrade.startsWith('A')) return 'grade-a';
    if (normalizedGrade.startsWith('B')) return 'grade-b';
    if (normalizedGrade.startsWith('C')) return 'grade-c';
    return 'grade-d';
};

const getDefenseClassName = (defenseRank) => {
    const rank = Number(defenseRank);
    if (!Number.isFinite(rank)) return '';
    if (rank <= 10) return 'opponent-top-defense';
    if (rank >= 23) return 'opponent-bottom-defense';
    return '';
};

function LineupOptimizer() {
    const [year, setYear] = useState('');
    const [week, setWeek] = useState('');
    const [stackQB, setStackQB] = useState(false);
    const [excludedPlayers, setExcludedPlayers] = useState(() => {
        try {
            const savedPlayers = window.localStorage.getItem(EXCLUDED_PLAYERS_STORAGE_KEY);
            const parsedPlayers = savedPlayers ? JSON.parse(savedPlayers) : [];
            return Array.isArray(parsedPlayers) ? parsedPlayers : [];
        } catch (error) {
            console.warn('Unable to restore excluded players:', error);
            return [];
        }
    });
    const [includedPlayers, setIncludedPlayers] = useState([]);
    const [lineups, setLineups] = useState([]);
    const [projections, setProjections] = useState([]);
    const [playerSearch, setPlayerSearch] = useState('');
    const [positionFilter, setPositionFilter] = useState('');
    const [teamFilter, setTeamFilter] = useState('');
    const [opponentFilter, setOpponentFilter] = useState('');
    const [kickoffCutoff, setKickoffCutoff] = useState('');
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('lineup1');
    const [playerPoolTab, setPlayerPoolTab] = useState('available');

    // Sorting state
    const [sortColumn, setSortColumn] = useState('salary');
    const [sortDirection, setSortDirection] = useState('desc');

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
        return projections.filter(projection => (
            projection.player?.toLowerCase().includes(playerSearch.toLowerCase()) &&
            (!positionFilter || projection.position === positionFilter) &&
            (!teamFilter || projection.team === teamFilter) &&
            (!opponentFilter || projection.opponent === opponentFilter) &&
            satisfiesKickoffCutoff(projection.kickoff, kickoffCutoff)
        ));
    }, [projections, playerSearch, positionFilter, teamFilter, opponentFilter, kickoffCutoff]);

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

    const isPlayerUnavailable = useCallback((player) => {
        if (excludedPlayers.includes(player.player)) return true;
        if (!player.kickoff) return false;

        const kickoffDate = new Date(player.kickoff);
        return !isNaN(kickoffDate.getTime()) && kickoffDate <= new Date();
    }, [excludedPlayers]);

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

    const toggleExclude = (playerName) => {
        const isCurrentlyExcluded = excludedPlayers.includes(playerName);
        const nextExcludedPlayers = isCurrentlyExcluded
            ? excludedPlayers.filter(player => player !== playerName)
            : [...excludedPlayers, playerName];
        const nextIncludedPlayers = isCurrentlyExcluded
            ? includedPlayers
            : includedPlayers.filter(player => player !== playerName);

        setExcludedPlayers(nextExcludedPlayers);
        setIncludedPlayers(nextIncludedPlayers);

        const appearsInSuggestedLineup = lineups.some(lineup => (
            lineup.some(player => player.player === playerName)
        ));

        if (!isCurrentlyExcluded && appearsInSuggestedLineup) {
            optimizeLineups(year, week, nextExcludedPlayers, nextIncludedPlayers);
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
        const nextExcludedPlayers = excludedPlayers.filter(player => player !== playerName);

        setIncludedPlayers(nextIncludedPlayers);
        setExcludedPlayers(nextExcludedPlayers);

        const appearsInSuggestedLineup = lineups.some(lineup => (
            lineup.some(player => player.player === playerName)
        ));

        if (!appearsInSuggestedLineup) {
            optimizeLineups(year, week, nextExcludedPlayers, nextIncludedPlayers);
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
                    className="action-button text-danger"
                    onClick={() => toggleExclude(playerName)}
                    title={`Restore ${playerName} to available players`}
                    aria-label={`Restore ${playerName} to available players`}
                >
                    <span role="img" aria-label="Restore">🚫</span>
                </button>
            );
        }

        return (
            <span className="player-actions">
                {!isIncluded && (
                    <button
                        type="button"
                        className="action-button text-danger"
                        onClick={() => toggleExclude(playerName)}
                        disabled={!canBeIncluded}
                        style={{
                            opacity: !canBeIncluded ? 0.35 : 1,
                            cursor: !canBeIncluded ? 'not-allowed' : 'pointer'
                        }}
                        title={!canBeIncluded ? check.reason : `Exclude ${playerName}`}
                        aria-label={`Exclude ${playerName}`}
                    >
                        <span role="img" aria-label="Exclude">🚫</span>
                    </button>
                )}
                <button
                    type="button"
                    className="action-button text-success"
                    onClick={() => toggleInclude(playerObj || playerName)}
                    disabled={!isIncluded && !canBeIncluded}
                    style={{
                        opacity: !isIncluded && !canBeIncluded ? 0.35 : 1,
                        cursor: !canBeIncluded && !isIncluded ? 'not-allowed' : 'pointer'
                    }}
                    title={isIncluded ? `Unlock ${playerName}` : (!canBeIncluded ? check.reason : `Include/Lock ${playerName}`)}
                    aria-label={`Include or Lock ${playerName}`}
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
                stack_qb: stackQB,
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
        }
    };

    const fetchCurrentPeriod = async () => {
        const yearResponse = await axios.get(`${BASE_URL_API}/projections/current_year`);
        const weekResponse = await axios.get(`${BASE_URL_API}/projections/current_week`);
        const currentYear = String(yearResponse.data);
        const currentWeek = String(weekResponse.data);
        setYear(currentYear);
        setWeek(currentWeek);
        setKickoffCutoff(getDefaultCutoff());
        optimizeLineups(currentYear, currentWeek);
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        optimizeLineups();
    };

    useEffect(() => {
        try {
            window.localStorage.setItem(EXCLUDED_PLAYERS_STORAGE_KEY, JSON.stringify(excludedPlayers));
        } catch (error) {
            console.warn('Unable to persist excluded players:', error);
        }
    }, [excludedPlayers]);

    useEffect(() => {
        fetchCurrentPeriod().catch((error) => {
            console.error('Error loading current year and week:', error);
            toast.error('Unable to load the current year and week. Please try again.');
        });
    }, []);

    const renderProjectionTable = (players, emptyMessage, isUnavailable = false) => (
        <div className="player-table-wrap">
            <table className="table table-striped player-pool-table">
                <thead>
                    <tr>
                        {mainPlayerColumns.map(col => {
                            const isSortable = sortableColumns.includes(col);
                            const isSorted = sortColumn === col;

                            return (
                                <th
                                    key={col}
                                    onClick={() => isSortable && handleSort(col)}
                                    style={{ cursor: isSortable ? 'pointer' : 'default', userSelect: 'none' }}
                                    title={isSortable ? `Sort by ${columnLabels[col] || col}` : ''}
                                >
                                    {columnLabels[col] || col}
                                    {isSortable && (
                                        <span style={{ marginLeft: '4px', opacity: isSorted ? 1 : 0.4 }}>
                                            {isSorted ? (sortDirection === 'asc' ? '▲' : '▼') : '↕'}
                                        </span>
                                    )}
                                </th>
                            );
                        })}
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {players.length === 0 ? (
                        <tr>
                            <td className="empty-player-state" colSpan={mainPlayerColumns.length + 1}>{emptyMessage}</td>
                        </tr>
                    ) : players.map((player, playerIndex) => {
                        const isIncluded = includedPlayers.includes(player.player);
                        return (
                            <tr
                                key={`${player.player}-${playerIndex}`}
                                className={`${isIncluded ? 'row-player-locked' : ''} ${isUnavailable ? 'row-player-unavailable' : ''}`.trim()}
                            >
                                {mainPlayerColumns.map(col => (
                                    <td key={col} style={getCellStyle(col, player[col])}>
                                        {col === 'opponent' ? (
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
                                ['Position', positionFilter, setPositionFilter, 'position'],
                                ['Team', teamFilter, setTeamFilter, 'team'],
                                ['Opponent', opponentFilter, setOpponentFilter, 'opponent'],
                            ].map(([label, value, setter, field]) => (
                                <select key={field} className="form-select form-select-sm" value={value} onChange={(e) => setter(e.target.value)} aria-label={`Filter by ${label}`}>
                                    <option value="">All {label}s</option>
                                    {getFilterOptions(field).map(option => <option key={option} value={option}>{option}</option>)}
                                </select>
                            ))}
                        </div>
                    </div>
                    {renderProjectionTable(
                        displayedProjections,
                        playerPoolTab === 'available' ? 'No available players match these filters.' : 'No unavailable players match these filters.',
                        playerPoolTab === 'unavailable'
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
                                <button type="submit" className="btn btn-primary optimize-button">Optimize</button>
                                <div className="filter-grid">
                                    <div className="form-group">
                                        <label htmlFor="year">Year</label>
                                        <input
                                            type="number"
                                            id="year"
                                            className="form-control form-control-sm"
                                            value={year}
                                            onChange={(e) => setYear(e.target.value)}
                                            min="2024"
                                            max="2026"
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
                                        id="stack_qb"
                                        className="form-check-input"
                                        checked={stackQB}
                                        onChange={(e) => setStackQB(e.target.checked)}
                                    />
                                    <label className="form-check-label" htmlFor="stack_qb">
                                        Stack QB with WR/TE
                                    </label>
                                </div>
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
                                                        {lineup.map((player, playerIndex) => (
                                                            <tr
                                                                key={`${player.player}-${playerIndex}`}
                                                                className={includedPlayers.includes(player.player) ? 'row-player-locked' : ''}
                                                            >
                                                                {playerColumns.map(col => (
                                                                    <td key={col} style={getCellStyle(col, player[col])}>
                                                                        {col === 'player' ? (
                                                                            <div className="lineup-player-cell">
                                                                                <strong>{player.player}</strong>
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