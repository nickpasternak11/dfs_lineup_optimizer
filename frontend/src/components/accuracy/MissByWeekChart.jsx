import React, { useState } from 'react';
import useWidth from '../../hooks/useWidth';
import { formatCount, formatMetric, sourceColor, weekLabel } from '../../lib/accuracy';
import { niceScale } from '../../lib/chartScale';
import '../charts/charts.css';

const MARGIN = { top: 12, right: 12, bottom: 30, left: 34 };
const HEIGHT = 250;
// Empty slots between seasons, so a line never joins one season to the next.
const SEASON_GAP = 1.5;
const MIN_LABEL_SPACING = 30;

const isMissing = value => value === null || value === undefined;

// Each week's x slot, with a gap at every change of season.
const slotsFor = (weeks) => {
    let slot = 0;
    return weeks.map((week, i) => {
        if (i > 0 && week.year !== weeks[i - 1].year) slot += SEASON_GAP;
        const at = slot;
        slot += 1;
        return at;
    });
};

// Runs of consecutive indexes in the same season.
const seasonRuns = weeks => weeks.reduce((runs, week, i) => {
    const last = runs[runs.length - 1];
    if (last && last.year === week.year) last.indexes.push(i);
    else runs.push({ year: week.year, indexes: [i] });
    return runs;
}, []);

// Average miss per week, one line per source: is the projection
// consistently better than the baseline, or only on average? A crosshair
// snaps to the nearest week; arrow keys move it.
export default function MissByWeekChart({ weeks, sources, metric = 'mae' }) {
    const [ref, width] = useWidth(560);
    const [active, setActive] = useState(null);

    if (!weeks.length) return null;

    const value = (week, source) => week.metrics[source.key]?.[metric];
    const slots = slotsFor(weeks);
    const lastSlot = slots[slots.length - 1];
    const plotWidth = Math.max(width - MARGIN.left - MARGIN.right, 120);
    const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
    const x = i => MARGIN.left + (lastSlot === 0 ? plotWidth / 2 : (slots[i] / lastSlot) * plotWidth);
    const values = weeks.flatMap(week => sources.map(source => value(week, source))).filter(v => !isMissing(v));
    const scale = niceScale(0, Math.max(...values));
    const y = v => MARGIN.top + plotHeight * (1 - (v - scale.min) / (scale.max - scale.min));
    const runs = seasonRuns(weeks);
    const multiSeason = runs.length > 1;

    // One path per source per season; a missing value breaks the line.
    const pathFor = (source, indexes) => indexes.reduce((d, i, n) => {
        const v = value(weeks[i], source);
        if (isMissing(v)) return d;
        const joined = n > 0 && !isMissing(value(weeks[indexes[n - 1]], source));
        return `${d}${joined ? 'L' : 'M'}${x(i)},${y(v)} `;
    }, '');

    // Week labels for one season; season labels, centered on their weeks, for several.
    const labelEvery = Math.max(1, Math.ceil(MIN_LABEL_SPACING / (plotWidth / Math.max(lastSlot, 1))));
    const xLabels = multiSeason
        ? runs.map(run => ({
            key: run.year,
            at: (x(run.indexes[0]) + x(run.indexes[run.indexes.length - 1])) / 2,
            text: String(run.year),
        }))
        : weeks
            .map((week, i) => ({ key: i, at: x(i), text: `W${week.week}` }))
            .filter((_, i) => i % labelEvery === 0);
    // Seasons with only a few weeks (2018-23 hold two each) would be short
    // dashes; their dots show they're data.
    const dottedIndexes = new Set(runs.filter(run => run.indexes.length <= 3).flatMap(run => run.indexes));

    const nearest = (pointerX) => {
        let best = 0;
        weeks.forEach((_, i) => { if (Math.abs(x(i) - pointerX) < Math.abs(x(best) - pointerX)) best = i; });
        return best;
    };
    const onPointerMove = (event) => {
        const box = event.currentTarget.getBoundingClientRect();
        setActive(nearest(event.clientX - box.left));
    };
    const onKeyDown = (event) => {
        const moves = { ArrowLeft: -1, ArrowRight: 1 };
        if (event.key in moves) {
            event.preventDefault();
            setActive(i => Math.min(Math.max((i ?? weeks.length - 1) + moves[event.key], 0), weeks.length - 1));
        } else if (event.key === 'Home' || event.key === 'End') {
            event.preventDefault();
            setActive(event.key === 'Home' ? 0 : weeks.length - 1);
        }
    };
    const shown = active === null ? null : weeks[active];
    const span = `${weekLabel(weeks[0])} to ${weekLabel(weeks[weeks.length - 1])}`;

    return (
        <figure className="line-chart">
            <figcaption className="chart-legend">
                {sources.map((source, s) => (
                    <span key={source.key}>
                        <span className="legend-swatch legend-line" style={{ background: sourceColor(source.key, s) }} />
                        {source.label}
                    </span>
                ))}
            </figcaption>
            <div
                className="chart-frame chart-focusable"
                ref={ref}
                tabIndex={0}
                role="group"
                aria-label={`Average miss by week, ${span}. Use the arrow keys to read each week.`}
                onKeyDown={onKeyDown}
                onFocus={() => setActive(i => i ?? weeks.length - 1)}
                onBlur={() => setActive(null)}
            >
                <svg width={width} height={HEIGHT} aria-hidden="true">
                    {scale.ticks.map(tick => (
                        <g key={tick} className="chart-grid">
                            <line x1={MARGIN.left} x2={width - MARGIN.right} y1={y(tick)} y2={y(tick)} />
                            <text x={MARGIN.left - 6} y={y(tick)} dy="0.32em" textAnchor="end">{tick}</text>
                        </g>
                    ))}
                    {xLabels.map(label => (
                        <text key={label.key} className="chart-x" x={label.at} y={HEIGHT - MARGIN.bottom + 18} textAnchor="middle">
                            {label.text}
                        </text>
                    ))}
                    {shown && (
                        <line className="chart-crosshair" x1={x(active)} x2={x(active)} y1={MARGIN.top} y2={HEIGHT - MARGIN.bottom} />
                    )}
                    {sources.map((source, s) => (
                        <g key={source.key} style={{ color: sourceColor(source.key, s) }}>
                            {runs.map(run => (
                                <path key={run.year} className="chart-line" d={pathFor(source, run.indexes)} />
                            ))}
                            {[...dottedIndexes].filter(i => !isMissing(value(weeks[i], source))).map(i => (
                                <circle key={i} className="chart-point" cx={x(i)} cy={y(value(weeks[i], source))} r={4} />
                            ))}
                            {shown && !isMissing(value(shown, source)) && (
                                <circle className="chart-point" cx={x(active)} cy={y(value(shown, source))} r={4.5} />
                            )}
                        </g>
                    ))}
                    {/* The whole plot is the hit target: the crosshair finds the week. */}
                    <rect
                        className="chart-hit"
                        x={MARGIN.left - 8}
                        y={MARGIN.top}
                        width={plotWidth + 16}
                        height={plotHeight}
                        onPointerMove={onPointerMove}
                        onPointerLeave={() => setActive(null)}
                    />
                </svg>
                {shown && (
                    <div
                        className="chart-tooltip"
                        style={{
                            left: Math.min(Math.max(x(active), 90), width - 90),
                            top: Math.max(y(Math.max(...sources.map(source => value(shown, source) ?? 0))) - 10, 0),
                        }}
                        role="status"
                    >
                        <strong>{weekLabel(shown)}</strong>
                        {sources.map((source, s) => (
                            <span key={source.key} className="tooltip-row">
                                <span className="tooltip-key-line" style={{ background: sourceColor(source.key, s) }} />
                                {source.label} {formatMetric(metric, value(shown, source))}
                            </span>
                        ))}
                        <span className="tooltip-meta">{formatCount(shown.player_weeks)} player-weeks</span>
                    </div>
                )}
            </div>
        </figure>
    );
}
