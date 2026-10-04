import React, { useState } from 'react';
import { toast } from 'react-toastify';
import { SALARY_CAP } from '../../lib/constants';
import { formatMatchup, formatPoints, formatSalary } from '../../lib/format';
import { formatKickoff } from '../../lib/kickoff';
import { orderLineup } from '../../lib/lineupOrder';
import { InjuryBadge, PositionBadge } from '../common/Badges';
import Icon from '../common/Icon';
import PlayerActions from '../common/PlayerActions';
import PlayerAvatar from '../common/PlayerAvatar';
import TeamLogo from '../common/TeamLogo';

const asText = slots => slots
    .map(({ slot, player }) => `${slot.padEnd(4)} ${player.player} (${player.team}) ${formatSalary(player.salary)}`)
    .join('\n');

const copyToClipboard = async (text) => {
    if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return;
    }
    // Plain http (e.g. the app on a LAN address) has no clipboard API.
    const area = document.createElement('textarea');
    area.value = text;
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    const copied = document.execCommand('copy');
    document.body.removeChild(area);
    if (!copied) throw new Error('copy failed');
};

// `projection` maps player names to their unblended projection, so every
// lineup is totalled on the same basis; proj_fpts in lineups 2 and 3 is the
// blended score they were optimized on.
export default function LineupCard({ lineup, strategy, projection, optimizer }) {
    const [copied, setCopied] = useState(false);
    const slots = orderLineup(lineup);
    const pointsFor = player => projection[player.player] ?? player.proj_fpts;
    const totalPoints = lineup.reduce((sum, p) => sum + (pointsFor(p) || 0), 0);
    const optimizedScore = lineup.reduce((sum, p) => sum + (p.proj_fpts || 0), 0);
    const salary = lineup.reduce((sum, p) => sum + (p.salary || 0), 0);
    const salaryShare = Math.min(100, (salary / SALARY_CAP) * 100);
    const isBlend = Math.abs(optimizedScore - totalPoints) >= 0.05;

    const copy = () => copyToClipboard(asText(slots))
        .then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
        })
        .catch(() => toast.error('Could not copy the lineup.'));

    return (
        <div className="lineup-card">
            <div className="lineup-summary">
                <div className="summary-points">
                    <span className="summary-value num">{formatPoints(totalPoints)}</span>
                    <span className="summary-label">projected pts</span>
                    {isBlend && (
                        <span className="summary-sub num" title="The blended score this lineup was optimized on">
                            {formatPoints(optimizedScore)} blended
                        </span>
                    )}
                </div>
                <div className="summary-salary">
                    <div className="summary-salary-text num">
                        <span>{formatSalary(salary)}</span>
                        <span className="muted">{formatSalary(SALARY_CAP - salary)} left</span>
                    </div>
                    <div className="salary-bar" role="img" aria-label={`${Math.round(salaryShare)}% of the salary cap used`}>
                        <span style={{ width: `${salaryShare}%` }} />
                    </div>
                </div>
                <button type="button" className="icon-button" onClick={copy} title="Copy lineup" aria-label="Copy lineup">
                    <Icon name={copied ? 'check' : 'copy'} />
                </button>
            </div>
            <p className="strategy-detail">{strategy.detail}</p>

            <ol className="roster">
                {slots.map(({ slot, player }) => {
                    const isLocked = optimizer.locked.includes(player.player);
                    return (
                        <li key={player.player} className={`roster-row ${isLocked ? 'is-locked' : ''}`}>
                            <PositionBadge position={slot === 'FLEX' ? 'flex' : player.position} label={slot} />
                            <PlayerAvatar player={player} size={38} />
                            <span className="roster-player">
                                <span className="roster-name">
                                    {player.player}
                                    <InjuryBadge player={player} />
                                </span>
                                <span className="roster-meta" title={[player.team, formatMatchup(player), formatKickoff(player.kickoff)].filter(Boolean).join(' · ')}>
                                    <TeamLogo team={player.team} size={14} />
                                    {' '}{player.team} {formatMatchup(player)}
                                    {player.kickoff && <span className="kickoff"> · {formatKickoff(player.kickoff)}</span>}
                                </span>
                            </span>
                            <span className="roster-numbers num">
                                <span className="roster-points">{formatPoints(pointsFor(player))}</span>
                                <span className="roster-salary">{formatSalary(player.salary)}</span>
                            </span>
                            <PlayerActions player={player} optimizer={optimizer} />
                        </li>
                    );
                })}
            </ol>
        </div>
    );
}
