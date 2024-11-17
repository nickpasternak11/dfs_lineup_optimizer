import React, { useState } from 'react';
import axios from 'axios';
import 'bootstrap/dist/css/bootstrap.min.css';
import './LineupOptimizer.css';

const protocol = window.location.protocol;
export const BASE_HOSTNAME = window.location.hostname;
export const BASE_URL = `${protocol}//${BASE_HOSTNAME}`;
export const BASE_URL_API = `${BASE_URL}:8080`;

function LineupOptimizer() {
    const [week, setWeek] = useState('');
    const [dst, setDst] = useState('');
    const [oneTe, setOneTe] = useState(false);
    const [excludedPlayers, setExcludedPlayers] = useState([]);
    const [includedPlayers, setIncludedPlayers] = useState([]);
    const [lineups, setLineups] = useState([]);
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('lineup1');

    const columnOrder = ["year", "week", "player", "position", "team", "opponent", "grade", "rank", "avg_fpts", "proj_fpts", "salary"];

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        const data = {
            week: week ? parseInt(week) : null,
            dst: dst || null,
            one_te: oneTe,
            excluded_players: excludedPlayers,
            included_players: includedPlayers
        };
        try {
            const response = await axios.post(`${BASE_URL_API}/optimize`, data);
            setLineups(response.data);
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while optimizing. Please try again.');
        } finally {
            setLoading(false);
        }
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

    return (
        <div className="container">
            <h1 className="text-center mb-4">DFS Lineup Optimizer</h1>
            <form onSubmit={handleSubmit} className="d-flex align-items-center justify-content-center mb-4">
                <div className="form-group me-2">
                    <label htmlFor="week">WEEK:</label>
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
                <div className="form-group me-2">
                    <label htmlFor="dst">DST:</label>
                    <input
                        type="text"
                        id="dst"
                        className="form-control form-control-sm"
                        value={dst}
                        onChange={(e) => setDst(e.target.value)}
                    />
                </div>
                <div className="form-group me-2">
                    <label htmlFor="one_te">MAX 1 TE:</label>
                    <input
                        type="checkbox"
                        id="one_te"
                        className="form-check-input"
                        checked={oneTe}
                        onChange={(e) => setOneTe(e.target.checked)}
                    />
                </div>
                <button type="submit" className="btn btn-primary btn-sm">Optimize</button>
            </form>

            <div className="row">
                <div className="col-md-2 mb-3 side-panel p-3">
                    <div id="excluded-players" className="mb-3">
                        <h6>Excluded Players:</h6>
                        <ul className="player-list">
                            {excludedPlayers.map(player => (
                                <li key={player} className="player-item">
                                    {player}
                                    <span className="text-danger action-button" onClick={() => toggleExclude(player)}>❌</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div id="included-players" className="mt-3">
                        <h6>Included Players:</h6>
                        <ul className="player-list">
                            {includedPlayers.map(player => (
                                <li key={player} className="player-item">
                                    {player}
                                    <span className="text-success action-button" onClick={() => toggleInclude(player)}>❌</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>

                <div className="col-md-10">
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
                                        <table className="table table-striped">
                                            <thead>
                                                <tr>
                                                    {columnOrder.map(col => (
                                                        <th key={col}>{col.charAt(0).toUpperCase() + col.slice(1)}</th>
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
                                                                    <span className="action-button text-danger" onClick={() => toggleExclude(player.player)}>❌</span>
                                                                    <span className="action-button text-success" onClick={() => toggleInclude(player.player)}>✅</span>
                                                                </>
                                                            )}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

export default LineupOptimizer;