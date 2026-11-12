import React, { useState } from 'react';
import { errorMessage } from '../../api/client';
import { formatPoints } from '../../lib/format';
import Icon from '../common/Icon';
import LineupCard from './LineupCard';
import OptimizerSettings from './OptimizerSettings';
import './LineupPanel.css';

export default function LineupPanel({ optimizer, onReviewExcluded }) {
    const { lineups, lineupError, optimizing, refresh } = optimizer;
    const [active, setActive] = useState(0);
    const shown = Math.min(active, Math.max(lineups.length - 1, 0));
    const current = lineups[shown];

    // Each lineup's players carry its own source's projection as proj_fpts.
    const totalFor = lineup => lineup.reduce((sum, p) => sum + (p.proj_fpts ?? 0), 0);

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
                        <div className="lineup-tabs" role="tablist" aria-label="Projection source">
                            {lineups.map(({ source, label, detail, lineup }, index) => (
                                <button
                                    key={source}
                                    type="button"
                                    role="tab"
                                    aria-selected={shown === index}
                                    onClick={() => setActive(index)}
                                    title={detail}
                                >
                                    <span className="lineup-tab-label">{label}</span>
                                    <span className="lineup-tab-points num">{lineup ? formatPoints(totalFor(lineup)) : '—'}</span>
                                </button>
                            ))}
                        </div>
                        {current.lineup ? (
                            <LineupCard key={current.source} lineup={current.lineup} detail={current.detail} optimizer={optimizer} />
                        ) : (
                            <div className="lineup-message">
                                <strong>No {current.label} lineup</strong>
                                <span>{errorMessage(current.error, 'The optimizer could not build this lineup.')}</span>
                            </div>
                        )}
                    </>
                )}
            </div>
        </section>
    );
}
