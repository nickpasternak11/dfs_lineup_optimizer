import React from 'react';
import { formatPoints, formatSalary } from '../../lib/format';
import { opponentLabel, resultLabel, weekLabel } from '../../lib/playerInfo';
import TeamLogo from '../common/TeamLogo';

const STAT_COLUMNS = {
    QB: [
        ['C/A', g => `${g.completions}/${g.attempts}`],
        ['Pass Yds', g => g.passing_yards],
        ['Pass TD', g => g.passing_tds],
        ['INT', g => g.interceptions],
        ['Rush Yds', g => g.rushing_yards],
        ['Rush TD', g => g.rushing_tds],
    ],
    RB: [
        ['Car', g => g.carries],
        ['Rush Yds', g => g.rushing_yards],
        ['Rush TD', g => g.rushing_tds],
        ['Tgt', g => g.targets],
        ['Rec', g => g.receptions],
        ['Rec Yds', g => g.receiving_yards],
        ['Rec TD', g => g.receiving_tds],
    ],
    WR: [
        ['Tgt', g => g.targets],
        ['Rec', g => g.receptions],
        ['Rec Yds', g => g.receiving_yards],
        ['Rec TD', g => g.receiving_tds],
        ['Rush Yds', g => g.rushing_yards],
    ],
    DST: [
        ['PA', g => g.points_allowed ?? '–'],
        ['Sacks', g => g.sacks],
        ['INT', g => g.interceptions],
        ['FR', g => g.fumble_recoveries],
        ['TD', g => g.defensive_tds + g.return_tds],
        ['Saf', g => g.safeties],
        ['Blk', g => g.blocked_kicks],
    ],
};
STAT_COLUMNS.TE = STAT_COLUMNS.WR;

export default function GameLogTable({ games, position }) {
    const stats = STAT_COLUMNS[position] || STAT_COLUMNS.WR;
    // Most recent game first: that's the one people look for.
    const rows = [...games].reverse();

    return (
        <div className="game-log-wrap">
            <table className="game-log">
                <thead>
                    <tr>
                        <th>Wk</th>
                        <th>Opp</th>
                        <th>Result</th>
                        <th className="align-right">FPTS</th>
                        <th className="align-right">Proj</th>
                        <th className="align-right">Salary</th>
                        {stats.map(([label]) => <th key={label} className="align-right">{label}</th>)}
                    </tr>
                </thead>
                <tbody>
                    {rows.map(game => (
                        <tr key={`${game.year}-${game.week}`}>
                            <td>{weekLabel(game)}</td>
                            <td>
                                <span className="game-log-opp">
                                    <TeamLogo team={game.opponent} size={16} />
                                    {opponentLabel(game)}
                                </span>
                            </td>
                            <td className="muted">{resultLabel(game)}</td>
                            <td className="align-right num strong">{formatPoints(game.dk_points)}</td>
                            <td className="align-right num muted">{formatPoints(game.proj_fpts)}</td>
                            <td className="align-right num muted">{formatSalary(game.salary) || '–'}</td>
                            {stats.map(([label, value]) => (
                                <td key={label} className="align-right num">{value(game)}</td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
