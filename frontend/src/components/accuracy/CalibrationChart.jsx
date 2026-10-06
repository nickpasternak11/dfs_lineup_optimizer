import React, { useState } from 'react';
import useWidth from '../../hooks/useWidth';
import { formatCount, rangeLabel } from '../../lib/accuracy';
import { niceScale } from '../../lib/chartScale';
import { formatPoints } from '../../lib/format';
import '../charts/charts.css';

const MARGIN = { top: 22, right: 16, bottom: 38, left: 34 };
const HEIGHT = 250;

// Projected against actual on the same FPTS scale, one point per projection
// range (its average projection and average score). On the dashed diagonal,
// players scored exactly what they were projected; above it, more.
export default function CalibrationChart({ calibration, sources }) {
    const [ref, width] = useWidth(560);
    const [active, setActive] = useState(null);

    const series = sources
        .map((source, s) => ({ ...source, color: `var(--series-${s + 1})`, bins: calibration[source.key] || [] }))
        .filter(source => source.bins.length);
    if (!series.length) return null;

    const plotWidth = Math.max(width - MARGIN.left - MARGIN.right, 120);
    const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
    const values = series.flatMap(source => source.bins.flatMap(bin => [bin.predicted, bin.actual]));
    const scale = niceScale(Math.min(0, ...values), Math.max(...values));
    const fraction = v => (v - scale.min) / (scale.max - scale.min);
    const x = v => MARGIN.left + plotWidth * fraction(v);
    const y = v => MARGIN.top + plotHeight * (1 - fraction(v));
    const shown = active && series[active.series].bins[active.bin];

    return (
        <figure className="line-chart">
            <figcaption className="chart-legend">
                {series.map(source => (
                    <span key={source.key}>
                        <span className="legend-swatch legend-dot" style={{ background: source.color }} />
                        {source.label}
                    </span>
                ))}
                <span><span className="legend-swatch legend-reference" />Scored as projected</span>
            </figcaption>
            <div className="chart-frame" ref={ref}>
                <svg width={width} height={HEIGHT} role="group" aria-label="Average actual FPTS against average projected FPTS, by projection range">
                    {scale.ticks.map(tick => (
                        <g key={tick} className="chart-grid">
                            <line x1={MARGIN.left} x2={width - MARGIN.right} y1={y(tick)} y2={y(tick)} />
                            <text x={MARGIN.left - 6} y={y(tick)} dy="0.32em" textAnchor="end">{tick}</text>
                            <text x={x(tick)} y={HEIGHT - MARGIN.bottom + 16} textAnchor="middle">{tick}</text>
                        </g>
                    ))}
                    <text className="chart-axis-title" x={MARGIN.left} y={MARGIN.top - 10}>Actual FPTS</text>
                    <text className="chart-axis-title" x={width - MARGIN.right} y={HEIGHT - 4} textAnchor="end">
                        Projected FPTS
                    </text>
                    <line
                        className="chart-reference"
                        x1={x(scale.min)}
                        y1={y(scale.min)}
                        x2={x(scale.max)}
                        y2={y(scale.max)}
                    />
                    {series.map((source, s) => (
                        <g key={source.key} style={{ color: source.color }}>
                            <path
                                className="chart-line"
                                d={source.bins.map((bin, b) => `${b ? 'L' : 'M'}${x(bin.predicted)},${y(bin.actual)}`).join(' ')}
                            />
                            {source.bins.map((bin, b) => {
                                const isActive = active?.series === s && active?.bin === b;
                                return (
                                    <g
                                        key={b}
                                        className={`chart-mark ${isActive ? 'is-active' : ''}`}
                                        tabIndex={0}
                                        aria-label={`${source.label}, projected ${rangeLabel(bin)}: projected ${formatPoints(bin.predicted)}, `
                                            + `scored ${formatPoints(bin.actual)} on average, ${formatCount(bin.player_weeks)} player-weeks`}
                                        onPointerEnter={() => setActive({ series: s, bin: b })}
                                        onPointerLeave={() => setActive(null)}
                                        onFocus={() => setActive({ series: s, bin: b })}
                                        onBlur={() => setActive(null)}
                                    >
                                        {/* A hit target bigger than the dot. */}
                                        <circle className="chart-hit" cx={x(bin.predicted)} cy={y(bin.actual)} r={12} />
                                        <circle className="chart-point" cx={x(bin.predicted)} cy={y(bin.actual)} r={isActive ? 5.5 : 4.5} />
                                    </g>
                                );
                            })}
                        </g>
                    ))}
                </svg>
                {shown && (
                    <div
                        className="chart-tooltip"
                        style={{
                            left: Math.min(Math.max(x(shown.predicted), 90), width - 90),
                            top: Math.max(y(shown.actual) - 12, 0),
                        }}
                        role="status"
                    >
                        <strong>
                            {formatPoints(shown.actual)}
                            <span> FPTS scored on average</span>
                        </strong>
                        <span className="tooltip-row">
                            <span className="tooltip-key-dot" style={{ background: series[active.series].color }} />
                            {series[active.series].label} {rangeLabel(shown)}: projected {formatPoints(shown.predicted)}
                        </span>
                        <span className="tooltip-meta">{formatCount(shown.player_weeks)} player-weeks</span>
                    </div>
                )}
            </div>
        </figure>
    );
}
