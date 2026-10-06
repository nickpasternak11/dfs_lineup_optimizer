import React, { useEffect, useMemo, useRef, useState } from 'react';
import useGameLog from '../../hooks/useGameLog';
import { formatMatchup, formatPoints, formatSalary, formatValue } from '../../lib/format';
import { formatKickoff } from '../../lib/kickoff';
import { formatSpread, linesSummary } from '../../lib/lines';
import { matchupSummary, matchupTier, ordinal } from '../../lib/matchup';
import {
    ageOn, defaultSeason, formatDraft, formatHeight, seasonSummary, seasonsOf,
} from '../../lib/playerInfo';
import { getTeam } from '../../lib/teams';
import { GradeBadge, InjuryBadge, PositionBadge } from '../common/Badges';
import Icon from '../common/Icon';
import PlayerActions from '../common/PlayerActions';
import PlayerAvatar from '../common/PlayerAvatar';
import TeamLogo from '../common/TeamLogo';
import GameLogTable from './GameLogTable';
import PointsChart from './PointsChart';
import './PlayerModal.css';

const FOCUSABLE = 'button, [href], input, select, [tabindex]:not([tabindex="-1"])';

// Closes on Escape, keeps Tab inside the dialog, and hands focus back to
// whatever opened it.
const useDialog = (onClose) => {
    const dialogRef = useRef(null);
    // The latest onClose, without re-running the setup when it changes.
    const closeRef = useRef(onClose);
    closeRef.current = onClose;
    useEffect(() => {
        const opener = document.activeElement;
        const { overflow } = document.body.style;
        document.body.style.overflow = 'hidden';
        dialogRef.current?.querySelector('.modal-close')?.focus();

        const onKeyDown = (event) => {
            if (event.key === 'Escape') {
                closeRef.current();
                return;
            }
            if (event.key !== 'Tab' || !dialogRef.current) return;
            const focusable = [...dialogRef.current.querySelectorAll(FOCUSABLE)];
            if (!focusable.length) return;
            const [first, last] = [focusable[0], focusable[focusable.length - 1]];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        };
        document.addEventListener('keydown', onKeyDown);
        return () => {
            document.removeEventListener('keydown', onKeyDown);
            document.body.style.overflow = overflow;
            if (opener && opener.focus) opener.focus();
        };
    }, []);
    return dialogRef;
};

// The team's implied points, with the over/under and spread beneath.
function TeamTotalTile({ player }) {
    const implied = player.implied_total;
    if (implied === null || implied === undefined) return null;
    return (
        <Tile
            label="Total"
            note={`O/U ${player.game_total} · ${player.team} ${formatSpread(player.team_spread)}`}
            title={linesSummary(player)}
        >
            {formatPoints(implied)}
        </Tile>
    );
}

function Bio({ bio }) {
    if (!bio) return null;
    const parts = [
        ageOn(bio.birthdate) !== null && `Age ${ageOn(bio.birthdate)}`,
        formatHeight(bio.height),
        bio.weight && `${bio.weight} lbs`,
        bio.college,
        formatDraft(bio),
    ].filter(Boolean);
    return parts.length ? <p className="player-bio">{parts.join(' · ')}</p> : null;
}

// Green when the player beat our projection in most weeks, red when they fell
// short in most, plain on an even split.
const hitRateClass = ({ beat, projected }) => (
    beat * 2 > projected ? 'beat' : beat * 2 < projected ? 'missed' : ''
);

function Tile({ label, note, title, children }) {
    return (
        <div className="stat-tile" title={title}>
            <span className="stat-label">{label}</span>
            <span className="stat-value">{children}</span>
            {note && <span className="stat-note">{note}</span>}
        </div>
    );
}

// The opponent's rank against this position, e.g. "7th" over "17.1 a game to RBs".
function MatchupTile({ player }) {
    const rank = player.opp_fpts_allowed_rank;
    if (rank === null || rank === undefined) return null;
    return (
        <Tile
            label={`${player.opponent} vs ${player.position}`}
            note={`${formatPoints(player.opp_fpts_allowed)} a game allowed`}
            title={matchupSummary(player)}
        >
            <span className={matchupTier(rank)}>{ordinal(rank)}</span>
        </Tile>
    );
}

export default function PlayerModal({ player, unavailableReason, optimizer, slateYear, onClose }) {
    const dialogRef = useDialog(onClose);
    const log = useGameLog(player);
    const games = useMemo(() => (log.status === 'ready' ? log.data.games : []), [log]);
    const [season, setSeason] = useState(null);
    const seasons = seasonsOf(games);
    const shownSeason = seasons.includes(season) ? season : defaultSeason(games, slateYear);
    const seasonGames = games.filter(g => g.year === shownSeason);
    const summary = seasonSummary(seasonGames);
    const team = getTeam(player.team);
    const titleId = 'player-modal-title';

    return (
        <div className="modal-backdrop" onMouseDown={event => event.target === event.currentTarget && onClose()}>
            <div className="player-modal" role="dialog" aria-modal="true" aria-labelledby={titleId} ref={dialogRef}>
                <header className="player-modal-header">
                    <PlayerAvatar player={player} size={64} />
                    <div className="player-modal-heading">
                        <h2 id={titleId}>
                            {player.player}
                            <InjuryBadge player={player} />
                        </h2>
                        <p className="player-modal-meta">
                            <PositionBadge position={player.position} />
                            {/* A defense's title is already its team name. */}
                            {player.position !== 'DST' && (
                                <>
                                    <TeamLogo team={player.team} size={16} />
                                    {team?.name || player.team}
                                </>
                            )}
                            {player.opponent && (
                                <span className="player-modal-matchup">
                                    · {formatMatchup(player)}
                                    {player.kickoff && ` · ${formatKickoff(player.kickoff)}`}
                                </span>
                            )}
                        </p>
                        <Bio bio={log.status === 'ready' ? log.data.player : null} />
                    </div>
                    <div className="player-modal-actions">
                        <PlayerActions player={player} unavailableReason={unavailableReason} optimizer={optimizer} />
                        <button type="button" className="icon-button modal-close" onClick={onClose} aria-label="Close">
                            <Icon name="close" size={18} />
                        </button>
                    </div>
                </header>

                <div className="stat-tiles">
                    <Tile label="Salary">{formatSalary(player.salary)}</Tile>
                    <Tile label="Projected">{formatPoints(player.proj_fpts)}</Tile>
                    {player.actual_dk_points !== null && player.actual_dk_points !== undefined && (
                        <Tile label="Actual">{formatPoints(player.actual_dk_points)}</Tile>
                    )}
                    <Tile label="Value">{formatValue(player.value)}</Tile>
                    <Tile label="Recent avg">{formatPoints(player.avg_fpts)}</Tile>
                    <MatchupTile player={player} />
                    <TeamTotalTile player={player} />
                    {player.grade && <Tile label="Grade"><GradeBadge grade={player.grade} /></Tile>}
                </div>

                <section className="player-modal-log" aria-label="Game log">
                    {log.status === 'loading' && (
                        <div className="log-placeholder">
                            <span className="skeleton" style={{ height: 240 }} />
                        </div>
                    )}
                    {log.status === 'error' && <p className="log-message">{log.error}</p>}
                    {log.status === 'unlinked' && (
                        <p className="log-message">
                            No game log: this player couldn&apos;t be matched to NFL stats.
                        </p>
                    )}
                    {log.status === 'ready' && !games.length && (
                        <p className="log-message">No NFL games yet.</p>
                    )}
                    {log.status === 'ready' && games.length > 0 && (
                        <>
                            <div className="log-toolbar">
                                <div className="segmented" role="group" aria-label="Season">
                                    {seasons.map(year => (
                                        <button
                                            key={year}
                                            type="button"
                                            aria-pressed={year === shownSeason}
                                            onClick={() => setSeason(year)}
                                        >
                                            {year}
                                        </button>
                                    ))}
                                </div>
                                <p className="log-summary num">
                                    {summary.games} {summary.games === 1 ? 'game' : 'games'}
                                    {' · '}avg {formatPoints(summary.average)} FPTS
                                    {' · '}best {formatPoints(summary.best)}
                                    {summary.projected > 0 && (
                                        <>
                                            {' · '}
                                            <span className={hitRateClass(summary)}>
                                                beat our projection {summary.beat} of {summary.projected}
                                            </span>
                                            {' · '}avg {summary.vsProjection >= 0 ? '+' : ''}
                                            {summary.vsProjection.toFixed(1)}/game
                                        </>
                                    )}
                                </p>
                            </div>
                            <PointsChart
                                key={shownSeason}
                                games={seasonGames}
                                title={`${player.player}: FPTS per game, ${shownSeason}`}
                            />
                            <GameLogTable games={seasonGames} position={player.position} />
                        </>
                    )}
                </section>
            </div>
        </div>
    );
}
