import React, { useState } from 'react';
import useAccuracy from '../../hooks/useAccuracy';
import {
    biasSentence, differenceLabel, formatCount, formatMetric, METRICS, rangeLabel, tierLabel, weekLabel,
} from '../../lib/accuracy';
import { formatPoints } from '../../lib/format';
import CalibrationChart from './CalibrationChart';
import MetricTable from './MetricTable';
import MissByWeekChart from './MissByWeekChart';
import './AccuracyPage.css';

const POSITIONS = ['QB', 'RB', 'WR', 'TE', 'DST'];
const MIN_PROJECTIONS = [
    { value: 0, label: 'All' },
    { value: 5, label: '5+' },
    { value: 10, label: '10+' },
];
const TILE_METRICS = ['mae', 'within', 'rank_corr', 'bias'];

function Filters({ filters, setFilter, seasons }) {
    return (
        <div className="accuracy-filters" role="group" aria-label="Filters">
            <label className="accuracy-filter">
                <span>Season</span>
                <select
                    className="select"
                    value={filters.year ?? ''}
                    onChange={e => setFilter('year', e.target.value ? Number(e.target.value) : null)}
                >
                    <option value="">All seasons</option>
                    {seasons.map(year => <option key={year} value={year}>{year}</option>)}
                </select>
            </label>
            <div className="accuracy-filter">
                <span id="accuracy-position">Position</span>
                <div className="segmented" role="group" aria-labelledby="accuracy-position">
                    {[null, ...POSITIONS].map(position => (
                        <button
                            key={position ?? 'all'}
                            type="button"
                            aria-pressed={filters.position === position}
                            onClick={() => setFilter('position', position)}
                        >
                            {position ?? 'All'}
                        </button>
                    ))}
                </div>
            </div>
            <div className="accuracy-filter">
                <span id="accuracy-min" title="A player counts when either source projected them for this many FPTS">
                    Projected
                </span>
                <div className="segmented" role="group" aria-labelledby="accuracy-min">
                    {MIN_PROJECTIONS.map(option => (
                        <button
                            key={option.value}
                            type="button"
                            aria-pressed={filters.minProj === option.value}
                            onClick={() => setFilter('minProj', option.value)}
                        >
                            {option.label}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}

// The first source's value, with every other source's beside it and how the
// first compares.
function SummaryTile({ metric, summary, sources }) {
    const [main, ...others] = sources;
    const value = summary.metrics[main.key]?.[metric];
    return (
        <div className="accuracy-tile" title={METRICS[metric].description}>
            <span className="stat-label">{METRICS[metric].label}</span>
            <span className="accuracy-tile-value num">
                {formatMetric(metric, value)}
                {metric === 'mae' && value !== null && <span className="accuracy-tile-unit"> FPTS</span>}
            </span>
            {metric === 'bias' && <span className="accuracy-tile-note">{biasSentence(value)}</span>}
            {others.map((other) => {
                const otherValue = summary.metrics[other.key]?.[metric];
                const difference = differenceLabel(metric, value, otherValue);
                return (
                    <span key={other.key} className="accuracy-tile-note">
                        {other.label} {formatMetric(metric, otherValue)}
                        {difference && (
                            <span className={difference.endsWith('better') ? 'is-good' : 'is-bad'}>
                                {' · '}{difference.endsWith('better') ? '▲' : '▼'} {difference}
                            </span>
                        )}
                    </span>
                );
            })}
        </div>
    );
}

function CoverageNote({ report }) {
    const { coverage, year, position, min_proj: minProj } = report;
    const since = year ? `in ${year}` : `since ${Math.min(...report.seasons)}`;
    const who = minProj > 0 ? `players either source projected for ${minProj}+ FPTS` : 'every player in the pool';
    const left = [
        coverage.no_stats && `${formatCount(coverage.no_stats)} inactive`,
        coverage.unlinked && `${formatCount(coverage.unlinked)} not matched to NFL stats`,
        coverage.no_baseline && `${formatCount(coverage.no_baseline)} with no recent games to average`,
    ].filter(Boolean);
    return (
        <p className="accuracy-coverage">
            {formatCount(coverage.evaluated)} player-weeks with a final game {since}: {who}
            {position && ` at ${position}`}.
            {left.length > 0 && ` Not compared: ${left.join(', ')}.`}
        </p>
    );
}

function ChartData({ summary, children }) {
    return (
        <details className="chart-data">
            <summary>{summary}</summary>
            <div className="metric-table-wrap">{children}</div>
        </details>
    );
}

export default function AccuracyPage() {
    const [filters, setFilters] = useState({ year: null, position: null, minProj: 5 });
    const setFilter = (name, value) => setFilters(prev => ({ ...prev, [name]: value }));
    const { status, data: report, error } = useAccuracy(filters);
    const sources = report?.sources || [];

    return (
        <main className="accuracy-page" aria-busy={status === 'loading'}>
            <header className="accuracy-intro">
                <h1>Projection accuracy</h1>
                <p>
                    How the projections compared with the DraftKings points players actually scored, every
                    week we have, against a simple baseline: each player&apos;s recent average. Each week is
                    judged only on what was known before it. The projection is FantasyPros&apos; full-PPR
                    number, so DraftKings&apos; yardage bonuses show up as bias.
                </p>
            </header>

            <Filters filters={filters} setFilter={setFilter} seasons={report?.seasons || []} />

            {status === 'error' && <p className="accuracy-message">{error}</p>}
            {!report && status === 'loading' && <div className="skeleton accuracy-skeleton" />}

            {report && report.summary.player_weeks === 0 && (
                <p className="accuracy-message">No finished games match these filters yet.</p>
            )}

            {report && report.summary.player_weeks > 0 && (
                <div className={`accuracy-body ${status === 'loading' ? 'is-stale' : ''}`.trim()}>
                    <div className="accuracy-tiles">
                        {TILE_METRICS.map(metric => (
                            <SummaryTile key={metric} metric={metric} summary={report.summary} sources={sources} />
                        ))}
                    </div>
                    <CoverageNote report={report} />

                    <div className="accuracy-charts">
                        <section className="card accuracy-card" aria-labelledby="miss-by-week">
                            <h2 id="miss-by-week">Average miss by week</h2>
                            <p className="accuracy-card-lead">FPTS off per player, lower is better.</p>
                            <MissByWeekChart weeks={report.by_week} sources={sources} />
                            <ChartData summary="Show the weeks as a table">
                                <table className="metric-table">
                                    <thead>
                                        <tr>
                                            <th scope="col">Week</th>
                                            <th scope="col" className="align-right">Player-weeks</th>
                                            {sources.map(source => (
                                                <th key={source.key} scope="col" className="align-right">{source.label}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {report.by_week.map(week => (
                                            <tr key={weekLabel(week)}>
                                                <th scope="row">{weekLabel(week)}</th>
                                                <td className="align-right num">{formatCount(week.player_weeks)}</td>
                                                {sources.map(source => (
                                                    <td key={source.key} className="align-right num">
                                                        {formatMetric('mae', week.metrics[source.key]?.mae)}
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </ChartData>
                        </section>

                        <section className="card accuracy-card" aria-labelledby="calibration">
                            <h2 id="calibration">Calibration</h2>
                            <p className="accuracy-card-lead">
                                What players scored, on average, for each range of projection. Points above the
                                dashed line scored more than projected.
                            </p>
                            <CalibrationChart calibration={report.calibration} sources={sources} />
                            <ChartData summary="Show the ranges as a table">
                                <table className="metric-table">
                                    <thead>
                                        <tr>
                                            <th scope="col">Source</th>
                                            <th scope="col">Projected</th>
                                            <th scope="col" className="align-right">Player-weeks</th>
                                            <th scope="col" className="align-right">Avg projected</th>
                                            <th scope="col" className="align-right">Avg scored</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {sources.flatMap(source => (report.calibration[source.key] || []).map(bin => (
                                            <tr key={`${source.key}-${bin.low}`}>
                                                <th scope="row">{source.label}</th>
                                                <td>{rangeLabel(bin)}</td>
                                                <td className="align-right num">{formatCount(bin.player_weeks)}</td>
                                                <td className="align-right num">{formatPoints(bin.predicted)}</td>
                                                <td className="align-right num">{formatPoints(bin.actual)}</td>
                                            </tr>
                                        )))}
                                    </tbody>
                                </table>
                            </ChartData>
                            {report.min_proj > 0 && (
                                <p className="accuracy-footnote">
                                    A player counts when either source projected them for {report.min_proj}+, so the
                                    lowest range holds players only the other source rated highly.
                                </p>
                            )}
                        </section>
                    </div>

                    <section className="card accuracy-card">
                        <MetricTable
                            caption="By position"
                            rows={report.by_position}
                            sources={sources}
                            rowHeader="Position"
                            rowLabel={row => row.position}
                            isSelected={row => row.position === report.position}
                        />
                    </section>
                    <section className="card accuracy-card">
                        <MetricTable
                            caption="By salary"
                            rows={report.by_salary}
                            sources={sources}
                            rowHeader="Salary"
                            rowLabel={tierLabel}
                        />
                    </section>
                </div>
            )}
        </main>
    );
}
