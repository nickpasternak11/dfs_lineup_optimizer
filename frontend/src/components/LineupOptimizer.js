import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import './LineupOptimizer.css';

const protocol = window.location.protocol;
export const BASE_HOSTNAME = window.location.hostname;
export const BASE_URL = `${protocol}//${BASE_HOSTNAME}`;
export const BASE_URL_API = `${BASE_URL}:8080`;

const columnOrder = ["year", "week", "player", "position", "team", "opponent", "grade", "rank", "avg_fpts", "proj_fpts", "salary"];
const columnLabels = {
    avg_fpts: "Mean FPTS",
    proj_fpts: "Proj FPTS",
};


function LineupOptimizer() {
    const [year, setYear] = useState('');
    const [week, setWeek] = useState('');
    const [dst, setDst] = useState('');
    const [oneTe, setOneTe] = useState(false);
    const [excludedPlayers, setExcludedPlayers] = useState([]);
    const [includedPlayers, setIncludedPlayers] = useState([]);
    const [lineups, setLineups] = useState([]);
    const [projections, setProjections] = useState([]);
    const [playerSearch, setPlayerSearch] = useState('');
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('lineup1');

    const players = [...new Set(
        projections
            .map(projection => projection.player)
            .filter(Boolean)
    )].sort();

    const filteredPlayers = players.filter(player =>
        player.toLowerCase().includes(playerSearch.toLowerCase())
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
                dst: dst || null,
                one_te: oneTe,
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
                                <input type="number" id="year" className="form-control form-control-sm" value={year} onChange={(e) => setYear(e.target.value)} min="2024" max="2026" />
                            </div>
                            <div className="form-group">
                                <label htmlFor="week">Week</label>
                                <input type="number" id="week" className="form-control form-control-sm" value={week} onChange={(e) => setWeek(e.target.value)} min="1" max="18" />
                            </div>
                        </div>
                        <div className="form-group">
                            <label htmlFor="dst">Defense</label>
                            <input type="text" id="dst" className="form-control form-control-sm" value={dst} onChange={(e) => setDst(e.target.value)} placeholder="Optional team" />
                        </div>
                        <label className="te-toggle" htmlFor="one_te">
                            <span>Limit to one TE</span>
                            <input type="checkbox" id="one_te" className="form-check-input" checked={oneTe} onChange={(e) => setOneTe(e.target.checked)} />
                        </label>
                        <button type="submit" className="btn btn-primary optimize-button">Optimize lineups</button>
                    </form>

                    <div className="player-search mb-3">
                        <div className="panel-heading compact-heading">
                            <span className="panel-kicker">Player pool</span>
                        </div>
                        <input
                            type="search"
                            id="player-search"
                            className="form-control form-control-sm"
                            value={playerSearch}
                            onChange={(e) => setPlayerSearch(e.target.value)}
                            placeholder="Search by name"
                        />
                        {playerSearch.trim() && (
                            <ul className="player-list search-results">
                                {filteredPlayers.map(player => (
                                    <li key={player} className="player-item search-result">
                                        <span>{player}</span>
                                        <span className="player-actions">
                                            <button
                                                type="button"
                                                className="btn btn-outline-danger btn-sm"
                                                onClick={() => toggleExclude(player)}
                                                disabled={excludedPlayers.includes(player)}
                                                title={`Exclude ${player}`}
                                            >
                                                ❌
                                            </button>
                                            <button
                                                type="button"
                                                className="btn btn-outline-success btn-sm"
                                                onClick={() => toggleInclude(player)}
                                                disabled={includedPlayers.includes(player)}
                                                title={`Include ${player}`}
                                            >
                                                ✅
                                            </button>
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>
                    <div id="excluded-players" className="player-group">
                        <h3>Excluded <span>{excludedPlayers.length}</span></h3>
                        <ul className="player-list">
                            {excludedPlayers.map(player => (
                                <li key={player} className="player-item">
                                    {player}
                                    <span className="text-danger action-button" role="button" tabIndex="0" onClick={() => toggleExclude(player)} onKeyDown={(e) => e.key === 'Enter' && toggleExclude(player)} aria-label={`Remove ${player} from excluded players`} title={`Remove ${player} from excluded players`}>❌</span>
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
                                    <span className="text-success action-button" role="button" tabIndex="0" onClick={() => toggleInclude(player)} onKeyDown={(e) => e.key === 'Enter' && toggleInclude(player)} aria-label={`Remove ${player} from included players`} title={`Remove ${player} from included players`}>❌</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                </aside>

                <main className="lineups-main">
                    <div className="lineups-heading">
                        <div>
                            <p className="eyebrow">Optimization results</p>
                        </div>
                    </div>
                    {loading && (
                        <div className="loader">
                            <div></div>
                        </div>
                    )}
                    {lineups.length > 0 && (
                        <>
                            <ul className="nav nav-tabs mb-2" id="lineupTabs" role="tablist">
                                {lineups.map((_, index) => (
                                    <li key={index} className="nav-item" role="presentation">
                                        <button
                                            className={`nav-link ${activeTab === `lineup${index + 1}` ? 'active' : ''}`}
                                            onClick={() => setActiveTab(`lineup${index + 1}`)}
                                        >
                                            Lineup {index + 1}
                                        </button>
                                    </li>
                                ))}
                            </ul>
                            <div className="tab-content">
                                {lineups.map((lineup, index) => (
                                    <div
                                        key={index}
                                        className={`tab-pane fade ${activeTab === `lineup${index + 1}` ? 'show active' : ''}`}
                                    >
                                        <div className="lineup-summary">
                                            Total Projected FPTS: {lineup.reduce((sum, player) => sum + player.proj_fpts, 0).toFixed(2)} - Total Cap: ${lineup.reduce((sum, player) => sum + player.salary, 0)}
                                        </div>
                                        <div className="lineup-table-wrap">
                                            <table className="table table-striped">
                                                <thead>
                                                    <tr>
                                                        {columnOrder.map(col => (
                                                            <th key={col}>{columnLabels[col] || col.charAt(0).toUpperCase() + col.slice(1)}</th>
                                                        ))}
                                                        <th>Actions</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {lineup.map((player, playerIndex) => (
                                                        <tr key={playerIndex}>
                                                            {columnOrder.map(col => (
                                                                <td key={col}>{player[col]}</td>
                                                            ))}
                                                            <td>
                                                                {!excludedPlayers.includes(player.player) && !includedPlayers.includes(player.player) && (
                                                                    <>
                                                                        <span className="action-button text-danger" onClick={() => toggleExclude(player.player)} title={`Exclude ${player.player}`} aria-label={`Exclude ${player.player}`}>❌</span>
                                                                        <span className="action-button text-success" onClick={() => toggleInclude(player.player)} title={`Include ${player.player}`} aria-label={`Include ${player.player}`}>✅</span>
                                                                    </>
                                                                )}
                                                            </td>
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
                </main>
            </div>
        </div>
    );
}

export default LineupOptimizer;