import React, { useContext, useState } from 'react';
import { ThemeContext } from '../../hooks/useTheme';
import { getTeam, teamLogoUrl } from '../../lib/teams';
import './media.css';

// A team's logo, falling back to its abbreviation on its color when the logo
// is unknown or fails to load.
export default function TeamLogo({ team, size = 20 }) {
    const [failed, setFailed] = useState(false);
    const info = getTeam(team);
    const url = teamLogoUrl(team, useContext(ThemeContext));
    const style = { width: size, height: size };

    if (!team) return null;
    if (!url || failed) {
        return (
            <span
                className="team-logo team-logo-fallback"
                style={{ ...style, background: info?.color || 'var(--text-faint)', fontSize: size * 0.36 }}
                title={info?.name || team}
            >
                {team}
            </span>
        );
    }
    return (
        <img
            className="team-logo"
            src={url}
            alt={info?.name || team}
            title={info?.name || team}
            style={style}
            loading="lazy"
            onError={() => setFailed(true)}
        />
    );
}
