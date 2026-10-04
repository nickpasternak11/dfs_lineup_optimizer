import React from 'react';
import { formatSalaryChange, gradeTone, injuryLabel } from '../../lib/format';
import './badges.css';

export function PositionBadge({ position, label }) {
    return <span className={`pos-badge pos-${String(position).toLowerCase()}`}>{label || position}</span>;
}

export function GradeBadge({ grade }) {
    if (!grade) return null;
    return <span className={`grade-badge grade-${gradeTone(grade)}`}>{grade}</span>;
}

export function InjuryBadge({ player }) {
    const label = injuryLabel(player.injury_status);
    if (!label) return null;
    const detail = [player.injury_status, player.injury_type].filter(Boolean).join(' · ');
    return <span className={`injury-badge injury-${label.toLowerCase()}`} title={detail}>{label}</span>;
}

// The arrow keeps the direction readable without relying on color.
export function SalaryChange({ value }) {
    const text = formatSalaryChange(value);
    if (!text) return null;
    const amount = Number(value);
    const direction = amount > 0 ? 'up' : amount < 0 ? 'down' : 'flat';
    return (
        <span className={`salary-change salary-change-${direction}`}>
            {direction === 'up' && '▲ '}
            {direction === 'down' && '▼ '}
            {text.replace(/^[+−]/, '')}
        </span>
    );
}

// One pip per lineup, filled for the lineups the player is in.
export function ExposurePips({ indexes, total }) {
    if (!indexes || !total) return null;
    const names = indexes.map(i => i + 1).join(', ');
    return (
        <span className="exposure-pips" title={`In lineup${indexes.length > 1 ? 's' : ''} ${names}`}>
            {Array.from({ length: total }, (_, i) => (
                <span key={i} className={indexes.includes(i) ? 'pip pip-on' : 'pip'} />
            ))}
        </span>
    );
}
