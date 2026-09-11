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

const playerColumns = ["player", "position", "team", "opponent", "proj_fpts", "salary"];
const mainPlayerColumns = ["player", "position", "team", "opponent", "grade", "rank", "avg_fpts", "proj_fpts", "salary", "value"];
const sortableColumns = ["rank", "avg_fpts", "proj_fpts", "salary", "value"];

const columnLabels = {
    player: "Player",
    position: "Pos",
    team: "Team",
    opponent: "Opp",
    grade: "Grd",
    rank: "Rnk",
    avg_fpts: "Avg FPTS",
    proj_fpts: "Proj FPTS",
    salary: "Salary",
    value: "Val"
};

const formatCellValue = (key, val) => {
    if (val === null || val === undefined) return '';
    if (key === 'salary') return `$${Number(val).toLocaleString()}`;
    if (key === 'value') return Number(val).toFixed(2);
    return val;
};

function LineupOptimizer() {
    const [year, setYear] = useState('');
    const [week, setWeek] = useState('');
    const [stackQB, setStackQB] = useState(false);
    const [excludedPlayers, setExcludedPlayers] = useState([]);
    const [includedPlayers, setIncludedPlayers] = useState([]);
    const [lineups, setLineups] = useState([]);
    const [projections, setProjections] = useState([]);
    const [playerSearch, setPlayerSearch] = useState('');
    const [positionFilter, setPositionFilter] = useState('');
    const [teamFilter, setTeamFilter] = useState('');
    const [opponentFilter, setOpponentFilter] = useState('');
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('lineup1');

    // Sorting state
    const [sortColumn, setSortColumn] = useState('salary');
    const [sortDirection, setSortDirection] = useState('desc');

    const getFilterOptions = useCallback((field) => {
        return [...new Set(
            projections.map(projection => projection[field]).filter(Boolean)
        )].sort();
    }, [projections]);

    const filteredProjections = useMemo(() => {
        return projections.filter(projection => (
            projection.player?.toLowerCase().includes(playerSearch.toLowerCase()) &&
            (!positionFilter || projection.position === positionFilter) &&
            (!teamFilter || projection.team === teamFilter) &&
            (!opponentFilter || projection.opponent === opponentFilter)
        ));
    }, [projections, playerSearch, positionFilter, teamFilter, opponentFilter]);

    const handleSort = (col) => {
        if (!sortableColumns.includes(col)) return;

        if (sortColumn === col) {
            setSortDirection(prev => (prev === 'asc' ? 'desc' : 'asc'));
        } else {
            setSortColumn(col);
            setSortDirection(col === 'rank' ? 'asc' : 'desc');
        }
    };

    const sortedProjections = useMemo(() => {
        return [...filteredProjections].sort((a, b) => {
            if (!sortColumn) return 0;

            let valA = a[sortColumn];
            let valB = b[sortColumn];

            if (valA === null || valA === undefined) return 1;
            if (valB === null || valB === undefined) return -1;

            if (typeof valA === 'number' && typeof valB === 'number') {
                return sortDirection === 'asc' ? valA - valB : valB - valA;
            }

            valA = String(valA).toUpperCase();
            valB = String(valB).toUpperCase();

            if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
            if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
            return 0;
        });
    }, [filteredProjections, sortColumn, sortDirection]);

    const toggleExclude = (playerName) => {
        setExcludedPlayers(prev => {
            if (prev.includes(playerName)) {
                return prev.filter(p => p !== playerName);
            } else {
                setIncludedPlayers(inc => inc.filter(p => p !== playerName));
                return [...prev, playerName];
            }
        });
    };

    const toggleInclude = (playerName) => {
        setIncludedPlayers(prev => {
            if (prev.includes(playerName)) {
                return prev.filter(p => p !== playerName);
            } else {
                setExcludedPlayers(exc => exc.filter(p => p !== playerName));
                return [...prev, playerName];
            }
        });
    };

    const renderActionButtons = (playerName) => (
        <span className="player-actions">
            <button
                type="button"
                className="action-button text-danger"
                onClick={() => toggleExclude(playerName)}
                disabled={excludedPlayers.includes(playerName)}
                title={`Exclude ${playerName}`}
                aria-label={`Exclude ${playerName}`}
            >
                <span role="img" aria-label="Exclude">❌</span>
            </button>
            <button
                type="button"
                className="action-button text-success"
                onClick={() => toggleInclude(playerName)}
                disabled={includedPlayers.includes(playerName)}
                title={`Include ${playerName}`}
                aria-label={`Include ${playerName}`}
            >
                <span role="img" aria-label="Include">✅</span>
            </button>
        </span>
    );

    const fetchProjections = async (selectedYear = year, selectedWeek = week) => {
        const response = await axios.post(`${BASE_URL_API}/projections`, {
            year: selectedYear ? parseInt(selectedYear) : null,
            week: selectedWeek ? parseInt(selectedWeek) : null,
        });
        setProjections(response.data);
    };

    const optimizeLineups = async (selectedYear = year, selectedWeek = week) => {
        setLoading(true);
        try {
            const data = {
                year: selectedYear ? parseInt(selectedYear) : null,
                week: selectedWeek ? parseInt(selectedWeek) : null,
                stack_qb: stackQB,
                excluded_players: excludedPlayers,
                included_players: includedPlayers
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
        optimizeLineups(currentYear, currentWeek);
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        optimizeLineups();
    };

    useEffect(() => {
        fetchCurrentPeriod().catch((error) => {
            console.error('Error loading current year and week:', error);
            toast.error('Unable to load the current year and week. Please try again.');
        });
    }, []);

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
                <aside className="side-panel">
                    <form onSubmit={handleSubmit} className="optimizer-controls">
                        <div className="panel-heading">
                            <span className="panel-kicker">Settings</span>
                        </div>
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
                        <button type="submit" className="btn btn-primary optimize-button">Optimize lineups</button>
                    </form>

                    <div id="excluded-players" className="player-group">
                        <h3>Excluded <span>{excludedPlayers.length}</span></h3>
                        <ul className="player-list">
                            {excludedPlayers.map(player => (
                                <li key={player} className="player-item">
                                    {player}
                                    <span className="text-danger action-button" role="button" tabIndex="0" onClick={() => toggleExclude(player)} onKeyDown={(e) => e.key === 'Enter' && toggleExclude(player)} aria-label={`Remove ${player} from excluded players`} title={`Remove ${player} from excluded players`}><span role="img" aria-label="Remove">❌</span></span>
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div id="included-players" className="player-group">
                        <h3>Included <span>{includedPlayers.length}</span></h3>
                        <ul className="player-list">
                            {includedPlayers.map(player => (
                                <li key={player} className="player-item">
                                    {player}
                                    <span className="text-success action-button" role="button" tabIndex="0" onClick={() => toggleInclude(player)} onKeyDown={(e) => e.key === 'Enter' && toggleInclude(player)} aria-label={`Remove ${player} from included players`} title={`Remove ${player} from included players`}><span role="img" aria-label="Remove">❌</span></span>
                                </li>
                            ))}
                        </ul>
                    </div>
                </aside>

                <main className="player-pool-main">
                    <div className="section-heading">
                        <div>
                            <p className="eyebrow">Player pool</p>
                            <h2>Available players</h2>
                        </div>
                        <span className="result-count">{filteredProjections.length} players</span>
                    </div>
                    <div className="player-filters">
                        <input
                            type="search"
                            id="player-search"
                            className="form-control form-control-sm"
                            value={playerSearch}
                            onChange={(e) => setPlayerSearch(e.target.value)}
                            placeholder="Search players"
                        />
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
                                                    <span style={{ marginLeft: '4px', opacity: isSorted ? 1 : 0.35 }}>
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
                                {sortedProjections.map((player, playerIndex) => (
                                    <tr key={`${player.player}-${playerIndex}`}>
                                        {mainPlayerColumns.map(col => (
                                            <td key={col}>{formatCellValue(col, player[col])}</td>
                                        ))}
                                        <td>{renderActionButtons(player.player)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </main>

                <aside className="results-panel">
                    <div className="section-heading">
                        <div>
                            <p className="eyebrow">Optimization results</p>
                            <h2>Suggested lineups</h2>
                        </div>
                    </div>
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
                                        <div className="lineup-summary">
                                            <span>{lineup.reduce((sum, player) => sum + player.proj_fpts, 0).toFixed(2)} FPTS</span>
                                            <span>${lineup.reduce((sum, player) => sum + player.salary, 0).toLocaleString()}</span>
                                        </div>
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
                                                        <tr key={`${player.player}-${playerIndex}`}>
                                                            {playerColumns.map(col => (
                                                                <td key={col}>{formatCellValue(col, player[col])}</td>
                                                            ))}
                                                            <td>{renderActionButtons(player.player)}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}
                </aside>
            </div>
        </div>
    );
}

export default LineupOptimizer;