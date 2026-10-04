import React from 'react';
import { KICKOFF_CUTOFFS, POSITIONS, VALUE_PLAY_THRESHOLD } from '../../lib/constants';
import { getTeam } from '../../lib/teams';
import Icon from '../common/Icon';

const QUICK_FILTERS = [
    { value: 'value', label: `Value ${VALUE_PLAY_THRESHOLD}x+` },
    { value: 'lineups', label: 'In my lineups' },
    { value: 'locked', label: 'Locked' },
    { value: 'excluded', label: 'Excluded' },
];

const teamLabel = abbreviation => getTeam(abbreviation)?.name || abbreviation;

export default function PoolFilters({ playerPool, shown }) {
    const { filters, setFilter, clearFilters, hasActiveFilters, options } = playerPool;

    return (
        <div className="pool-filters">
            <div className="pool-filters-row">
                <div className="segmented" role="group" aria-label="Position">
                    {['', ...POSITIONS].map(position => (
                        <button
                            key={position || 'all'}
                            type="button"
                            aria-pressed={filters.position === position}
                            onClick={() => setFilter('position', position)}
                        >
                            {position || 'All'}
                        </button>
                    ))}
                </div>
                <label className="search-field">
                    <Icon name="search" />
                    <span className="visually-hidden">Search players</span>
                    <input
                        type="search"
                        className="input"
                        placeholder="Search players"
                        value={filters.search}
                        onChange={e => setFilter('search', e.target.value)}
                    />
                </label>
            </div>

            <div className="pool-filters-row">
                <select
                    className="select"
                    value={filters.cutoff}
                    onChange={e => setFilter('cutoff', e.target.value)}
                    aria-label="Games"
                >
                    {KICKOFF_CUTOFFS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
                <select
                    className="select"
                    value={filters.team}
                    onChange={e => setFilter('team', e.target.value)}
                    aria-label="Team"
                >
                    <option value="">All teams</option>
                    {options.team.map(team => <option key={team} value={team}>{teamLabel(team)}</option>)}
                </select>
                <select
                    className="select"
                    value={filters.opponent}
                    onChange={e => setFilter('opponent', e.target.value)}
                    aria-label="Opponent"
                >
                    <option value="">All opponents</option>
                    {options.opponent.map(team => <option key={team} value={team}>vs {teamLabel(team)}</option>)}
                </select>
            </div>

            <div className="pool-filters-row pool-filters-footer">
                <div className="quick-filters" role="group" aria-label="Quick filters">
                    {QUICK_FILTERS.map(({ value, label }) => (
                        <button
                            key={value}
                            type="button"
                            className="chip"
                            aria-pressed={filters.quick === value}
                            onClick={() => setFilter('quick', filters.quick === value ? '' : value)}
                        >
                            {label}
                        </button>
                    ))}
                </div>
                <div className="filter-summary">
                    <span className="num">{shown} {shown === 1 ? 'player' : 'players'}</span>
                    {hasActiveFilters && (
                        <button type="button" className="button button-ghost" onClick={clearFilters}>
                            <Icon name="close" size={14} />
                            Clear
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
