import React from 'react';
import { VALUE_PLAY_THRESHOLD } from '../../lib/constants';
import { formatMatchup, formatPoints, formatSalary, formatValue } from '../../lib/format';
import { formatKickoff } from '../../lib/kickoff';
import { ExposurePips, GradeBadge, InjuryBadge, PositionBadge, SalaryChange } from '../common/Badges';
import Icon from '../common/Icon';
import PlayerActions from '../common/PlayerActions';
import PlayerAvatar from '../common/PlayerAvatar';
import TeamLogo from '../common/TeamLogo';

const COLUMNS = [
    { key: 'player', label: 'Player' },
    { key: 'opponent', label: 'Matchup' },
    { key: 'grade', label: 'Grade', align: 'center' },
    { key: 'avg_fpts', label: 'Avg', title: 'Average fantasy points over recent games', sortable: true, align: 'right' },
    { key: 'proj_fpts', label: 'Proj', title: 'Projected fantasy points', sortable: true, align: 'right' },
    { key: 'salary', label: 'Salary', sortable: true, align: 'right' },
    { key: 'salary_change', label: 'Δ', title: 'Salary change since last week', sortable: true, align: 'right' },
    { key: 'value', label: 'Value', title: 'Projected points per $1,000 of salary', sortable: true, align: 'right' },
    { key: 'actions', label: <span className="visually-hidden">Actions</span>, align: 'right' },
];

const REASON_LABELS = { started: 'Started', excluded: 'Excluded', both: 'Started · Excluded' };

// Top-10 defenses make a tough matchup, bottom-10 a soft one.
const matchupTier = (rank) => {
    if (!Number.isFinite(Number(rank)) || rank === null) return '';
    if (rank <= 10) return 'matchup-tough';
    if (rank >= 23) return 'matchup-soft';
    return '';
};

function SortHeader({ column, sort, onSort }) {
    const active = sort.column === column.key;
    const ariaSort = active ? (sort.direction === 'asc' ? 'ascending' : 'descending') : 'none';
    return (
        <th className={`align-${column.align || 'left'}`} aria-sort={ariaSort} title={column.title}>
            <button type="button" className={`sort-button ${active ? 'is-active' : ''}`} onClick={() => onSort(column.key)}>
                {column.label}
                <Icon name={active ? (sort.direction === 'asc' ? 'sortUp' : 'sortDown') : 'sort'} size={12} />
            </button>
        </th>
    );
}

function SkeletonRows() {
    return Array.from({ length: 10 }, (_, i) => (
        <tr key={i} className="skeleton-row">
            <td>
                <span className="player-cell">
                    <span className="skeleton" style={{ width: 34, height: 34, borderRadius: '50%' }} />
                    <span style={{ flex: 1 }}>
                        <span className="skeleton" style={{ width: '60%', marginBottom: 6 }} />
                        <span className="skeleton" style={{ width: '35%', height: 10 }} />
                    </span>
                </span>
            </td>
            {COLUMNS.slice(1).map(column => (
                <td key={column.key}><span className="skeleton" /></td>
            ))}
        </tr>
    ));
}

export default function PoolTable({ rows, playerPool, optimizer, lineupCount, loading, emptyMessage }) {
    const { sort, toggleSort, exposure, defenseRank, unavailableReason } = playerPool;
    const { locked } = optimizer;

    return (
        <div className="pool-table-wrap">
            <table className="pool-table">
                <thead>
                    <tr>
                        {COLUMNS.map(column => (column.sortable ? (
                            <SortHeader key={column.key} column={column} sort={sort} onSort={toggleSort} />
                        ) : (
                            <th key={column.key} className={`align-${column.align || 'left'}`} title={column.title}>
                                {column.label}
                            </th>
                        )))}
                    </tr>
                </thead>
                <tbody>
                    {loading && <SkeletonRows />}
                    {!loading && rows.length === 0 && (
                        <tr>
                            <td className="empty-state" colSpan={COLUMNS.length}>{emptyMessage}</td>
                        </tr>
                    )}
                    {!loading && rows.map((player) => {
                        const reason = unavailableReason(player);
                        const isLocked = locked.includes(player.player);
                        return (
                            <tr
                                key={player.player}
                                className={`${isLocked ? 'row-locked' : ''} ${reason ? 'row-unavailable' : ''}`.trim()}
                            >
                                <td>
                                    <span className="player-cell">
                                        <PlayerAvatar player={player} size={34} />
                                        <span className="player-text">
                                            <span className="player-name">
                                                {player.player}
                                                <InjuryBadge player={player} />
                                                <ExposurePips indexes={exposure[player.player]} total={lineupCount} />
                                            </span>
                                            <span className="player-meta">
                                                <PositionBadge position={player.position} />
                                                <TeamLogo team={player.team} size={14} />
                                                {player.team}
                                                {reason && <span className={`reason-tag reason-${reason}`}>{REASON_LABELS[reason]}</span>}
                                            </span>
                                        </span>
                                    </span>
                                </td>
                                <td>
                                    <span className="matchup-cell">
                                        <TeamLogo team={player.opponent} size={18} />
                                        <span>
                                            <span
                                                className={`matchup ${matchupTier(defenseRank[player.opponent])}`}
                                                title={defenseRank[player.opponent] ? `${player.opponent} defense ranks #${defenseRank[player.opponent]} this week` : undefined}
                                            >
                                                {formatMatchup(player)}
                                            </span>
                                            <span className="kickoff">{formatKickoff(player.kickoff)}</span>
                                        </span>
                                    </span>
                                </td>
                                <td className="align-center"><GradeBadge grade={player.grade} /></td>
                                <td className="align-right num muted">{formatPoints(player.avg_fpts)}</td>
                                <td className="align-right num strong">{formatPoints(player.proj_fpts)}</td>
                                <td className="align-right num">{formatSalary(player.salary)}</td>
                                <td className="align-right num"><SalaryChange value={player.salary_change} /></td>
                                <td className="align-right num">
                                    <span className={Number(player.value) >= VALUE_PLAY_THRESHOLD ? 'value-hot' : ''}>{formatValue(player.value)}</span>
                                </td>
                                <td className="align-right">
                                    <PlayerActions player={player} unavailableReason={reason} optimizer={optimizer} />
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}
