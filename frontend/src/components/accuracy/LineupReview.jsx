import React, { useState } from 'react';
import useLineupReview from '../../hooks/useLineupReview';
import { formatPoints, formatSalary } from '../../lib/format';
import {
    finalLineup, formatSavedAt, formatSwing, lineupKey, lineupLabel, pairLineups, seasonSummary, shareOfBest,
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

function WeekSummary({ review, pairs }) {
    const best = review.best?.actual;
    const swapped = pairs.some(pair => pair.swap);
    return (
        <section className="card accuracy-card" aria-labelledby="week-summary">
            <h2 id="week-summary">Week {review.week}</h2>
            <p className="accuracy-card-lead">
                Saved {formatSavedAt(review.saved_at)}, before the week&apos;s first game
                {review.swapped_at && `, and swapped ${formatSavedAt(review.swapped_at)}: players whose games had started kept, the rest re-optimized`}.
                {!review.complete && ' Some games aren\'t final yet, so these are the points so far.'}
            </p>
            <div className="metric-table-wrap">
                <table className="metric-table">
                    <thead>
                        <tr>
                            <th scope="col">Lineup</th>
                            <th scope="col" className="align-right">Projected</th>
                            <th scope="col" className="align-right">{swapped ? 'Before swaps' : 'Actual'}</th>
                            {swapped && <th scope="col" className="align-right">After swaps</th>}
                            <th scope="col" className="align-right" title="Actual points as played, as a share of the best lineup in hindsight">
                                Of best
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {pairs.map((pair) => {
                            const played = finalLineup(pair);
                            return (
                                <tr key={pair.key}>
                                    <th scope="row">{lineupLabel(pair)}</th>
                                    <td className="align-right num">{formatPoints(pair.initial?.projected)}</td>
                                    <td className={`align-right num ${swapped ? '' : 'strong'}`.trim()}>{formatPoints(pair.initial?.actual)}</td>
                                    {swapped && (
                                        <td className="align-right num strong">
                                            {pair.swap ? formatPoints(pair.swap.actual) : '–'}
                                            {pair.swap && pair.initial && (
                                                <span className="swap-swing"> ({formatSwing(pair.swap.actual - pair.initial.actual)})</span>
                                            )}
                                        </td>
                                    )}
                                    <td className="align-right num">{shareOfBest(played.actual, best)}</td>
                                </tr>
                            );
                        })}
                        {review.best && (
                            <tr className="is-selected">
                                <th scope="row">Best possible, in hindsight</th>
                                <td className="align-right num">–</td>
                                <td className="align-right num strong">{swapped ? '–' : formatPoints(best)}</td>
                                {swapped && <td className="align-right num strong">{formatPoints(best)}</td>}
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
    const columns = pairLineups(review.season[review.season.length - 1].lineups);
    const { averages, swapGains } = seasonSummary(review.season);
    const bests = review.season.filter(week => week.complete && week.best !== null).map(week => week.best);
    const anySwaps = Object.keys(swapGains).length > 0;
    return (
        <section className="card accuracy-card">
            <div className="metric-table-wrap">
                <table className="metric-table">
                    <caption>{review.year} season: actual points, as played</caption>
                    <thead>
                        <tr>
                            <th scope="col">Week</th>
                            {columns.map(pair => (
                                <th key={pair.key} scope="col" className="align-right source-head">{lineupLabel(pair)}</th>
                            ))}
                            <th scope="col" className="align-right source-head">Best possible</th>
                        </tr>
                    </thead>
                    <tbody>
                        {review.season.map((week) => {
                            const played = Object.fromEntries(pairLineups(week.lineups).map(pair => [pair.key, finalLineup(pair).actual]));
                            return (
                                <tr key={week.week} className={week.week === review.week ? 'is-selected' : undefined}>
                                    <th scope="row">
                                        W{week.week}
                                        {!week.complete && <span className="muted"> (in progress)</span>}
                                    </th>
                                    {columns.map(pair => (
                                        <td key={pair.key} className="align-right num">{formatPoints(played[pair.key])}</td>
                                    ))}
                                    <td className="align-right num">{formatPoints(week.best)}</td>
                                </tr>
                            );
                        })}
                        <tr>
                            <th scope="row" title="Finished weeks only">Average</th>
                            {columns.map(pair => (
                                <td key={pair.key} className="align-right num strong">{formatPoints(averages[pair.key])}</td>
                            ))}
                            <td className="align-right num strong">
                                {bests.length ? formatPoints(bests.reduce((a, b) => a + b, 0) / bests.length) : '–'}
                            </td>
                        </tr>
                        {anySwaps && (
                            <tr>
                                <th scope="row" title="After Sunday's swaps minus before, on average, over finished weeks that had one">
                                    Swaps added
                                </th>
                                {columns.map(pair => (
                                    <td key={pair.key} className="align-right num">{formatSwing(swapGains[pair.key])}</td>
                                ))}
                                <td className="align-right num">–</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </section>
    );
}

// The lineups the optimizer suggested before each week's first game, on each
// projection source, and Sunday's late swap of them, scored on what their
// players did.
export default function LineupReview() {
    const [selected, setSelected] = useState(null);
    const { status, data: review, error } = useLineupReview(selected?.year ?? null, selected?.week ?? null);

    if (!review && status === 'loading') return <div className="skeleton accuracy-skeleton" />;
    if (status === 'error' && !review) return <p className="accuracy-message">{error}</p>;
    if (!review || review.weeks.length === 0) {
        return (
            <p className="accuracy-message">
                No saved lineups yet. They&apos;re saved at 9 AM ET on the day of each week&apos;s first game
                (usually Thursday), for the whole Thursday-to-Monday slate, on FantasyPros&apos; projections and
                our model&apos;s, and swapped Sunday at 11:50 AM ET.
            </p>
        );
    }

    const pairs = pairLineups(review.lineups);
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

            <WeekSummary review={review} pairs={pairs} />
            <SeasonTable review={review} />

            <section className="card accuracy-card">
                <h2>Rosters</h2>
                {pairs.flatMap(pair => [pair.initial, pair.swap].filter(Boolean)).map(lineup => (
                    <details key={`${lineup.phase}:${lineupKey(lineup)}`} className="chart-data">
                        <summary>
                            {lineupLabel(lineup)}{lineup.phase === 'late_swap' && ', after Sunday swaps'}:{' '}
                            {formatPoints(lineup.actual)} actual, {formatPoints(lineup.projected)} projected
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
