import React from 'react';
import { compareMetric, formatCount, formatMetric, METRICS } from '../../lib/accuracy';

const TABLE_METRICS = ['mae', 'within', 'rank_corr', 'bias'];

// One row per slice (a position, a salary tier), and under each metric a
// column per source. The better value of each pair is bold. A metric no row
// has (ranking by salary tier) is left out.
export default function MetricTable({ caption, rows, sources, rowLabel, rowHeader, isSelected = () => false }) {
    const metrics = TABLE_METRICS.filter(metric => rows.some(row => (
        sources.some(source => row.metrics[source.key]?.[metric] !== null && row.metrics[source.key]?.[metric] !== undefined)
    )));
    const isBetter = (row, metric, s) => sources.length > 1 && sources.every((other, o) => (
        o === s || compareMetric(metric, row.metrics[sources[s].key]?.[metric], row.metrics[other.key]?.[metric]) > 0
    ));

    return (
        <div className="metric-table-wrap">
            <table className="metric-table">
                <caption>{caption}</caption>
                <thead>
                    <tr>
                        <th rowSpan={2} scope="col">{rowHeader}</th>
                        <th rowSpan={2} scope="col" className="align-right">Player-weeks</th>
                        {metrics.map(metric => (
                            <th key={metric} colSpan={sources.length} scope="colgroup" className="metric-group" title={METRICS[metric].description}>
                                {METRICS[metric].label}
                            </th>
                        ))}
                    </tr>
                    <tr>
                        {metrics.flatMap(metric => sources.map(source => (
                            <th key={`${metric}-${source.key}`} scope="col" className="align-right source-head">{source.label}</th>
                        )))}
                    </tr>
                </thead>
                <tbody>
                    {rows.map(row => (
                        <tr key={rowLabel(row)} className={isSelected(row) ? 'is-selected' : undefined}>
                            <th scope="row">{rowLabel(row)}</th>
                            <td className="align-right num">{formatCount(row.player_weeks)}</td>
                            {metrics.flatMap(metric => sources.map((source, s) => (
                                <td
                                    key={`${metric}-${source.key}`}
                                    className={`align-right num ${isBetter(row, metric, s) ? 'is-better' : ''}`.trim()}
                                >
                                    {formatMetric(metric, row.metrics[source.key]?.[metric])}
                                </td>
                            )))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
