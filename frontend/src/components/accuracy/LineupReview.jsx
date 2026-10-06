import React, { useState } from 'react';
import useLineupReview from '../../hooks/useLineupReview';
import { formatPoints, formatSalary } from '../../lib/format';
import {
    formatSavedAt, lineupKey, lineupLabel, seasonAverages, shareOfBest,
} from '../../lib/lineupReview';

function Roster({ players, showProjection = true }) {
    return (
        <div className="metric-table-wrap roster-wrap">
            <table className="metric-table roster-table">
                <thead>
                    <tr>
                        <th scope="col">Pos</th>
                        <th scope="col">Player</th>
                        <th scope="col">Team</th>
                        <th scope="col" className="align-right">Salary</th>
                        {showProjection && <th scope="col" className="align-right">Projected</th>}
                        <th scope="col" className="align-right">Actual</th>
                    </tr>
                </thead>
                <tbody>
                    {players.map(player => (
                        <tr key={player.player}>
                            <td>{player.position}</td>
                            <th scope="row">{player.player}</th>
                            <td>{player.team}</td>
                            <td className="align-right num">{formatSalary(player.salary)}</td>
                            {showProjection && <td className="align-right num">{formatPoints(player.projection)}</td>}
                            <td className="align-right num">
                                {player.actual === null ? <span title="Didn't play, or the game isn't final">–</span> : formatPoints(player.actual)}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

function WeekSummary({ review }) {
    const best = review.best?.actual;
    return (
        <section className="card accuracy-card" aria-labelledby="week-summary">
            <h2 id="week-summary">Week {review.week}</h2>
            <p className="accuracy-card-lead">
                Saved {formatSavedAt(review.saved_at)}, from the games still to come.
                {!review.complete && ' Some of those games aren\'t final yet, so these are the points so far.'}
            </p>
            <div className="metric-table-wrap">
                <table className="metric-table">
                    <thead>
                        <tr>
                            <th scope="col">Lineup</th>
                            <th scope="col" className="align-right">Projected</th>
                            <th scope="col" className="align-right">Actual</th>
                            <th scope="col" className="align-right" title="Actual points as a share of the best lineup in hindsight">
                                Of best
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {review.lineups.map(lineup => (
                            <tr key={lineupKey(lineup)}>
                                <th scope="row">{lineupLabel(lineup)}</th>
                                <td className="align-right num">{formatPoints(lineup.projected)}</td>
                                <td className="align-right num strong">{formatPoints(lineup.actual)}</td>
                                <td className="align-right num">{shareOfBest(lineup.actual, best)}</td>
                            </tr>
                        ))}
                        {review.best && (
                            <tr className="is-selected">
                                <th scope="row">Best possible, in hindsight</th>
                                <td className="align-right num">–</td>
                                <td className="align-right num strong">{formatPoints(best)}</td>
                                <td className="align-right num">100%</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </section>
    );
}

function SeasonTable({ review }) {
    if (review.season.length < 2) return null;
    const columns = review.season[review.season.length - 1].lineups;
    const averages = seasonAverages(review.season);
    const average = values => values.reduce((a, b) => a + b, 0) / values.length;
    const bests = review.season.filter(week => week.complete && week.best !== null).map(week => week.best);
    return (
        <section className="card accuracy-card">
            <div className="metric-table-wrap">
                <table className="metric-table">
                    <caption>{review.year} season: actual points</caption>
                    <thead>
                        <tr>
                            <th scope="col">Week</th>
                            {columns.map(lineup => (
                                <th key={lineupKey(lineup)} scope="col" className="align-right source-head">{lineupLabel(lineup)}</th>
                            ))}
                            <th scope="col" className="align-right source-head">Best possible</th>
                        </tr>
                    </thead>
                    <tbody>
                        {review.season.map((week) => {
                            const byKey = Object.fromEntries(week.lineups.map(lineup => [lineupKey(lineup), lineup.actual]));
                            return (
                                <tr key={week.week} className={week.week === review.week ? 'is-selected' : undefined}>
                                    <th scope="row">
                                        W{week.week}
                                        {!week.complete && <span className="muted"> (in progress)</span>}
                                    </th>
                                    {columns.map(lineup => (
                                        <td key={lineupKey(lineup)} className="align-right num">{formatPoints(byKey[lineupKey(lineup)])}</td>
                                    ))}
                                    <td className="align-right num">{formatPoints(week.best)}</td>
                                </tr>
                            );
                        })}
                        <tr>
                            <th scope="row" title="Finished weeks only">Average</th>
                            {columns.map(lineup => (
                                <td key={lineupKey(lineup)} className="align-right num strong">{formatPoints(averages[lineupKey(lineup)])}</td>
                            ))}
                            <td className="align-right num strong">{bests.length ? formatPoints(average(bests)) : '–'}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </section>
    );
}

// The lineups the optimizer suggested before each week's games, on each
// projection source, scored on what their players did.
export default function LineupReview() {
    const [selected, setSelected] = useState(null);
    const { status, data: review, error } = useLineupReview(selected?.year ?? null, selected?.week ?? null);

    if (!review && status === 'loading') return <div className="skeleton accuracy-skeleton" />;
    if (status === 'error' && !review) return <p className="accuracy-message">{error}</p>;
    if (!review || review.weeks.length === 0) {
        return (
            <p className="accuracy-message">
                No saved lineups yet. They&apos;re saved every Sunday at 9 AM ET in season, for the Sunday and
                Monday games, on FantasyPros&apos; projections and our model&apos;s.
            </p>
        );
    }

    return (
        <div className={`accuracy-body ${status === 'loading' ? 'is-stale' : ''}`.trim()}>
            <div className="accuracy-filters">
                <label className="accuracy-filter">
                    <span>Week</span>
                    <select
                        className="select"
                        value={`${review.year}-${review.week}`}
                        onChange={(e) => {
                            const [year, week] = e.target.value.split('-').map(Number);
                            setSelected({ year, week });
                        }}
                    >
                        {review.weeks.map(ref => (
                            <option key={`${ref.year}-${ref.week}`} value={`${ref.year}-${ref.week}`}>
                                {ref.year} week {ref.week}
                            </option>
                        ))}
                    </select>
                </label>
            </div>

            <WeekSummary review={review} />
            <SeasonTable review={review} />

            <section className="card accuracy-card">
                <h2>Rosters</h2>
                {review.lineups.map(lineup => (
                    <details key={lineupKey(lineup)} className="chart-data">
                        <summary>
                            {lineupLabel(lineup)}: {formatPoints(lineup.actual)} actual, {formatPoints(lineup.projected)} projected
                        </summary>
                        <Roster players={lineup.players} />
                    </details>
                ))}
                {review.best && (
                    <details className="chart-data">
                        <summary>Best possible, in hindsight: {formatPoints(review.best.actual)}</summary>
                        <Roster players={review.best.players} showProjection={false} />
                    </details>
                )}
            </section>
        </div>
    );
}
