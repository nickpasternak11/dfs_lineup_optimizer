import React, { useState } from 'react';
import { initials } from '../../lib/format';
import { getTeam, headshotUrl } from '../../lib/teams';
import TeamLogo from './TeamLogo';
import './media.css';

// A player's headshot, or their team's logo for a defense. Players without a
// FantasyPros id (weeks scraped before it was stored) or whose image fails
// get their initials on the team color.
export default function PlayerAvatar({ player, size = 36 }) {
    const [failed, setFailed] = useState(false);
    const style = { width: size, height: size };

    if (player.position === 'DST') {
        return (
            <span className="avatar avatar-team" style={style}>
                <TeamLogo team={player.team} size={size * 0.78} />
            </span>
        );
    }

    const url = headshotUrl(player.fp_player_id);
    if (!url || failed) {
        return (
            <span
                className="avatar avatar-initials"
                style={{ ...style, background: getTeam(player.team)?.color || 'var(--text-faint)', fontSize: size * 0.36 }}
                aria-hidden="true"
            >
                {initials(player.player)}
            </span>
        );
    }
    return (
        <span className="avatar" style={style}>
            <img src={url} alt="" loading="lazy" onError={() => setFailed(true)} />
        </span>
    );
}
