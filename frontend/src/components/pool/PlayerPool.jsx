import React from 'react';
import PoolFilters from './PoolFilters';
import PoolTable from './PoolTable';
import './PlayerPool.css';

export default function PlayerPool({ optimizer, playerPool }) {
    const { tab, setTab, available, unavailable, rows, hasActiveFilters } = playerPool;
    const tabs = [
        { key: 'available', label: 'Available', count: available.length },
        { key: 'unavailable', label: 'Unavailable', count: unavailable.length },
    ];
    const emptyMessage = optimizer.pool.length === 0
        ? 'No player pool for this week yet.'
        : `No ${tab} players${hasActiveFilters ? ' match these filters' : ''}.`;

    return (
        <section className="card player-pool" aria-label="Player pool">
            <div className="card-header">
                <div>
                    <p className="eyebrow">Player pool</p>
                    <h2>Week {optimizer.slate.week || '–'} players</h2>
                </div>
                <div className="segmented" role="tablist" aria-label="Player status">
                    {tabs.map(({ key, label, count }) => (
                        <button
                            key={key}
                            type="button"
                            role="tab"
                            aria-selected={tab === key}
                            onClick={() => setTab(key)}
                        >
                            {label}
                            <span className={`tab-count ${key === 'unavailable' ? 'tab-count-muted' : ''}`}>{count}</span>
                        </button>
                    ))}
                </div>
            </div>
            <PoolFilters playerPool={playerPool} shown={rows.length} />
            <PoolTable
                rows={rows}
                playerPool={playerPool}
                optimizer={optimizer}
                lineupCount={optimizer.lineups.length}
                loading={optimizer.loadingPool}
                emptyMessage={emptyMessage}
            />
        </section>
    );
}
