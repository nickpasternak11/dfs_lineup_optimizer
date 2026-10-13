import React from 'react';
import { VIEWS } from '../../hooks/useView';
import { FIRST_SEASON, WEEKS_PER_SEASON } from '../../lib/constants';
import Icon from '../common/Icon';
import './AppHeader.css';

const range = (from, to) => Array.from({ length: to - from + 1 }, (_, i) => from + i);

export default function AppHeader({ view, slate, current, onChangeSlate, theme, onToggleTheme }) {
    const seasons = current.year ? range(FIRST_SEASON, Number(current.year)).reverse() : [];
    const isCurrent = slate.year === current.year && slate.week === current.week;
    const ready = Boolean(slate.year && slate.week);

    return (
        <header className="app-header">
            <div className="app-header-inner">
                <div className="brand">
                    <img src={`${import.meta.env.BASE_URL}favicon-192x192.png`} alt="" />
                    <div>
                        <span className="brand-name">DFS Lineup Optimizer</span>
                        <span className="brand-tagline">DraftKings NFL classic</span>
                    </div>
                </div>

                <nav className="app-nav" aria-label="Pages">
                    <a href={VIEWS.lineups.hash} aria-current={view === 'lineups' ? 'page' : undefined}>Lineups</a>
                    <a href={VIEWS.accuracy.hash} aria-current={view === 'accuracy' ? 'page' : undefined}>Accuracy</a>
                </nav>

                {/* The slate only applies to the lineups page; accuracy has its own filters. */}
                {view === 'lineups' && (
                    <div className="slate-picker" aria-label="Slate">
                        <label>
                            <span>Season</span>
                            <select
                                value={slate.year}
                                disabled={!ready}
                                onChange={e => onChangeSlate(e.target.value, slate.week)}
                            >
                                {seasons.map(year => <option key={year} value={year}>{year}</option>)}
                            </select>
                        </label>
                        <label>
                            <span>Week</span>
                            <select
                                value={slate.week}
                                disabled={!ready}
                                onChange={e => onChangeSlate(slate.year, e.target.value)}
                            >
                                {range(1, WEEKS_PER_SEASON).map(week => <option key={week} value={week}>{week}</option>)}
                            </select>
                        </label>
                        {ready && (isCurrent ? (
                            <span className="live-badge"><span className="live-dot" />This week</span>
                        ) : (
                            <button
                                type="button"
                                className="back-to-current"
                                onClick={() => onChangeSlate(current.year, current.week)}
                            >
                                Back to this week
                            </button>
                        ))}
                    </div>
                )}

                <button
                    type="button"
                    className="theme-toggle"
                    onClick={onToggleTheme}
                    aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
                    title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
                >
                    <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={18} />
                </button>
            </div>
        </header>
    );
}
