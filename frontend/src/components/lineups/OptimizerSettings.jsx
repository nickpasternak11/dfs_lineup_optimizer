import React from 'react';
import { ROSTER_SIZE, SALARY_CAP } from '../../lib/constants';
import { formatSalary } from '../../lib/format';
import Icon from '../common/Icon';

const STACK_OPTIONS = [
    { value: 0, label: 'Off' },
    { value: 1, label: '+1' },
    { value: 2, label: '+2' },
];

export default function OptimizerSettings({ optimizer, onReviewExcluded }) {
    const { settings, updateSettings, includeStarted, isPastSlate, locked, excluded, pool, toggleLock, clearLocks } = optimizer;
    const lockedPlayers = locked.map(name => pool.find(p => p.player === name)).filter(Boolean);
    const lockedSalary = lockedPlayers.reduce((sum, p) => sum + (p.salary || 0), 0);

    return (
        <div className="optimizer-settings">
            <div className="setting-row">
                <div>
                    <span className="setting-label">QB stack</span>
                    <span className="setting-hint">Pair the QB with his own WR/TE</span>
                </div>
                <div className="segmented" role="group" aria-label="QB stack">
                    {STACK_OPTIONS.map(({ value, label }) => (
                        <button
                            key={value}
                            type="button"
                            aria-pressed={settings.stackQbCount === value}
                            onClick={() => updateSettings({ stackQbCount: value })}
                        >
                            {label}
                        </button>
                    ))}
                </div>
            </div>
            <label className="switch setting-row">
                <span>
                    <span className="setting-label">Avoid TE in FLEX</span>
                </span>
                <input
                    type="checkbox"
                    role="switch"
                    checked={settings.avoidTeFlex}
                    onChange={e => updateSettings({ avoidTeFlex: e.target.checked })}
                />
            </label>
            <label className="switch setting-row">
                <span>
                    <span className="setting-label">Include started games</span>
                    <span className="setting-hint">
                        {isPastSlate ? 'Always on for a past week' : 'Allow players whose games already kicked off'}
                    </span>
                </span>
                <input
                    type="checkbox"
                    role="switch"
                    checked={includeStarted}
                    disabled={isPastSlate}
                    onChange={e => updateSettings({ includeStarted: e.target.checked })}
                />
            </label>

            <div className="locks">
                <div className="locks-header">
                    <span className="setting-label">
                        <Icon name="lock" size={13} /> Locked {locked.length}/{ROSTER_SIZE}
                        {locked.length > 0 && (
                            <span className="locks-salary num">
                                {' · '}{formatSalary(lockedSalary)} of {formatSalary(SALARY_CAP)}
                            </span>
                        )}
                    </span>
                    {locked.length > 0 && (
                        <button type="button" className="link-button" onClick={clearLocks}>Clear</button>
                    )}
                </div>
                {locked.length === 0 ? (
                    <p className="locks-empty">Lock players from the pool to force them into every lineup.</p>
                ) : (
                    <div className="lock-chips">
                        {lockedPlayers.map(player => (
                            <button
                                key={player.player}
                                type="button"
                                className="lock-chip"
                                onClick={() => toggleLock(player)}
                                title={`Unlock ${player.player}`}
                            >
                                {player.player}
                                <Icon name="close" size={12} />
                            </button>
                        ))}
                    </div>
                )}
                {excluded.length > 0 && (
                    <button type="button" className="link-button excluded-link" onClick={onReviewExcluded}>
                        {excluded.length} excluded this week · Review
                    </button>
                )}
            </div>
        </div>
    );
}
