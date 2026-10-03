import React, { useMemo, useState } from 'react';
import { LINEUP_STRATEGIES } from '../../lib/constants';
import { formatPoints } from '../../lib/format';
import Icon from '../common/Icon';
import LineupCard from './LineupCard';
import OptimizerSettings from './OptimizerSettings';
import './LineupPanel.css';

export default function LineupPanel({ optimizer, onReviewExcluded }) {
    const { lineups, lineupError, optimizing, refresh, pool } = optimizer;
    const [active, setActive] = useState(0);
    const shown = Math.min(active, Math.max(lineups.length - 1, 0));

    const projection = useMemo(() => {
        const byName = {};
        pool.forEach((p) => { byName[p.player] = p.proj_fpts; });
        return byName;
    }, [pool]);

    const totalFor = lineup => lineup.reduce((sum, p) => sum + (projection[p.player] ?? p.proj_fpts ?? 0), 0);

    return (
        <section className="card lineup-panel" aria-label="Lineups">
            <div className="card-header">
                <div>
                    <p className="eyebrow">Optimizer</p>
                    <h2>Suggested lineups</h2>
                </div>
                <button
                    type="button"
                    className="button"
                    onClick={refresh}
                    disabled={optimizing}
                    title="Reload the player pool and re-run the optimizer"
                >
                    <Icon name="refresh" size={14} className={optimizing ? 'spinner' : ''} />
                    {optimizing ? 'Optimizing' : 'Refresh'}
                </button>
            </div>

            <OptimizerSettings optimizer={optimizer} onReviewExcluded={onReviewExcluded} />

            <div className={`lineup-results ${optimizing ? 'is-busy' : ''}`} aria-busy={optimizing}>
                {lineupError && (
                    <div className="lineup-message">
                        <strong>No lineups</strong>
                        <span>{lineupError}</span>
                    </div>
                )}
                {!lineupError && lineups.length === 0 && (
                    <div className="lineup-message">
                        <span className="skeleton" style={{ width: '100%', height: 56 }} />
                        <span className="skeleton" style={{ width: '100%', height: 220 }} />
                    </div>
                )}
                {!lineupError && lineups.length > 0 && (
                    <>
                        <div className="lineup-tabs" role="tablist" aria-label="Lineup strategy">
                            {lineups.map((lineup, index) => (
                                <button
                                    key={index}
                                    type="button"
                                    role="tab"
                                    aria-selected={shown === index}
                                    onClick={() => setActive(index)}
                                    title={LINEUP_STRATEGIES[index]?.detail}
                                >
                                    <span className="lineup-tab-label">{LINEUP_STRATEGIES[index]?.label || `Lineup ${index + 1}`}</span>
                                    <span className="lineup-tab-points num">{formatPoints(totalFor(lineup))}</span>
                                </button>
                            ))}
                        </div>
                        <LineupCard
                            key={shown}
                            lineup={lineups[shown]}
                            strategy={LINEUP_STRATEGIES[shown] || { detail: '' }}
                            projection={projection}
                            optimizer={optimizer}
                        />
                    </>
                )}
            </div>
        </section>
    );
}
