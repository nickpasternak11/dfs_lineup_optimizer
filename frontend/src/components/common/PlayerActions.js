import React from 'react';
import { toast } from 'react-toastify';
import { canLockPlayer } from '../../lib/rosterRules';
import Icon from './Icon';

// Lock and exclude buttons for one player. Buttons whose action isn't allowed
// right now stay clickable and explain why in a toast: a disabled button
// never fires on touch screens, so its tooltip would be invisible on phones.
export default function PlayerActions({ player, unavailableReason, optimizer }) {
    const { locked, excluded, pool, toggleLock, toggleExclude } = optimizer;
    const name = player.player;
    const isLocked = locked.includes(name);
    const isExcluded = excluded.includes(name);

    if (unavailableReason === 'started') {
        return <span className="row-status">Started</span>;
    }
    if (isExcluded) {
        return (
            <button
                type="button"
                className="icon-button"
                onClick={() => toggleExclude(name)}
                title={`Restore ${name}`}
                aria-label={`Restore ${name}`}
            >
                <Icon name="undo" />
            </button>
        );
    }

    const lockCheck = isLocked ? { allowed: true } : canLockPlayer(player, locked, pool);
    return (
        <span className="row-actions">
            <button
                type="button"
                className={`icon-button ${isLocked ? 'is-active' : ''} ${lockCheck.allowed ? '' : 'is-blocked'}`}
                onClick={() => (lockCheck.allowed ? toggleLock(player) : toast.warning(lockCheck.reason))}
                title={isLocked ? `Unlock ${name}` : lockCheck.reason || `Lock ${name} into every lineup`}
                aria-label={isLocked ? `Unlock ${name}` : `Lock ${name}`}
                aria-pressed={isLocked}
            >
                <Icon name={isLocked ? 'lock' : 'unlock'} />
            </button>
            {!isLocked && (
                <button
                    type="button"
                    className="icon-button is-danger"
                    onClick={() => toggleExclude(name)}
                    title={`Exclude ${name}`}
                    aria-label={`Exclude ${name}`}
                >
                    <Icon name="ban" />
                </button>
            )}
        </span>
    );
}
