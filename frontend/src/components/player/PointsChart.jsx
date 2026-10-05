import React, { useEffect, useRef, useState } from 'react';
import { niceScale } from '../../lib/chartScale';
import { formatPoints } from '../../lib/format';
import { opponentLabel, resultLabel, weekLabel } from '../../lib/playerInfo';

const MARGIN = { top: 22, right: 8, bottom: 38, left: 34 };
const HEIGHT = 240;
const MAX_BAR = 24;
const RADIUS = 4;

// Width of the element, kept current as it resizes; the SVG is laid out in
// real pixels so its text never scales.
const useWidth = (fallback) => {
    const ref = useRef(null);
    const [width, setWidth] = useState(fallback);
    useEffect(() => {
        const element = ref.current;
        if (!element) return undefined;
        setWidth(element.clientWidth || fallback);
        if (typeof ResizeObserver === 'undefined') return undefined;
        const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width || fallback));
        observer.observe(element);
        return () => observer.disconnect();
    }, [fallback]);
    return [ref, width];
};

// A column with a 4px rounded data end and a square baseline; negative values
// hang below the zero line with the rounding at the bottom.
const columnPath = (x, width, zeroY, valueY) => {
    const r = Math.min(RADIUS, width / 2, Math.abs(zeroY - valueY));
    if (valueY <= zeroY) {
        return `M${x},${zeroY} V${valueY + r} Q${x},${valueY} ${x + r},${valueY} H${x + width - r} `
            + `Q${x + width},${valueY} ${x + width},${valueY + r} V${zeroY} Z`;
    }
    return `M${x},${zeroY} V${valueY - r} Q${x},${valueY} ${x + r},${valueY} H${x + width - r} `
        + `Q${x + width},${valueY} ${x + width},${valueY - r} V${zeroY} Z`;
};

// Actual DraftKings points per game as columns, our projection as a dot on
// the same axis. The game log table below is this chart's table view.
export default function PointsChart({ games, title }) {
    const [ref, width] = useWidth(640);
    const [active, setActive] = useState(null);

    if (!games.length) return null;

    const plotWidth = Math.max(width - MARGIN.left - MARGIN.right, 120);
    const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
    const values = games.flatMap(g => [g.dk_points, g.proj_fpts]).filter(v => v !== null && v !== undefined);
    const scale = niceScale(Math.min(...values), Math.max(...values));
    const y = value => MARGIN.top + plotHeight * (1 - (value - scale.min) / (scale.max - scale.min));
    const band = plotWidth / games.length;
    const barWidth = Math.min(MAX_BAR, band * 0.6);
    const center = index => MARGIN.left + band * (index + 0.5);
    const zeroY = y(0);
    const hasProjection = games.some(g => g.proj_fpts !== null && g.proj_fpts !== undefined);
    // Label only the best game, on its cap.
    const best = games.reduce((top, g, i) => (g.dk_points > games[top].dk_points ? i : top), 0);
    // Thin the x labels when the columns get narrow (a 20-game season on a phone).
    const labelEvery = band < 26 ? 2 : 1;
    const shown = active === null ? null : games[active];

    return (
        <figure className="points-chart">
            <figcaption className="chart-legend">
                <span><span className="legend-swatch legend-bar" />Actual FPTS</span>
                {hasProjection && <span><span className="legend-swatch legend-dot" />Our projection</span>}
            </figcaption>
            <div className="chart-frame" ref={ref}>
                <svg width={width} height={HEIGHT} role="img" aria-label={title}>
                    {scale.ticks.map(tick => (
                        <g key={tick} className="chart-grid">
                            <line x1={MARGIN.left} x2={width - MARGIN.right} y1={y(tick)} y2={y(tick)} />
                            <text x={MARGIN.left - 6} y={y(tick)} dy="0.32em" textAnchor="end">{tick}</text>
                        </g>
                    ))}
                    {games.map((game, i) => {
                        const x = center(i) - barWidth / 2;
                        const proj = game.proj_fpts;
                        const label = `${weekLabel(game)} ${opponentLabel(game)}: ${formatPoints(game.dk_points)} FPTS`
                            + `${proj !== null && proj !== undefined ? `, projected ${formatPoints(proj)}` : ''}`;
                        return (
                            <g
                                key={`${game.year}-${game.week}`}
                                className={`chart-game ${active === i ? 'is-active' : ''}`}
                                onPointerEnter={() => setActive(i)}
                                onPointerLeave={() => setActive(null)}
                                onFocus={() => setActive(i)}
                                onBlur={() => setActive(null)}
                                tabIndex={0}
                                aria-label={label}
                            >
                                {/* The whole band is the hit target, not just the column. */}
                                <rect className="chart-hit" x={center(i) - band / 2} y={MARGIN.top} width={band} height={plotHeight} />
                                <path className="chart-bar" d={columnPath(x, barWidth, zeroY, y(game.dk_points))} />
                                {proj !== null && proj !== undefined && (
                                    <circle className="chart-dot" cx={center(i)} cy={y(proj)} r={4.5} />
                                )}
                                {i === best && (
                                    <text className="chart-value" x={center(i)} y={y(Math.max(game.dk_points, 0)) - 6} textAnchor="middle">
                                        {formatPoints(game.dk_points)}
                                    </text>
                                )}
                                {i % labelEvery === 0 && (
                                    <text className="chart-x" x={center(i)} y={HEIGHT - MARGIN.bottom + 14} textAnchor="middle">
                                        <tspan x={center(i)}>{weekLabel(game)}</tspan>
                                        <tspan x={center(i)} dy="1.25em" className="chart-x-opp">
                                            {game.home === false ? '@' : ''}{game.opponent}
                                        </tspan>
                                    </text>
                                )}
                            </g>
                        );
                    })}
                    <line className="chart-zero" x1={MARGIN.left} x2={width - MARGIN.right} y1={zeroY} y2={zeroY} />
                </svg>
                {shown && (
                    <div
                        className="chart-tooltip"
                        style={{ left: Math.min(Math.max(center(active), 80), width - 80), top: Math.max(y(Math.max(shown.dk_points, shown.proj_fpts ?? 0)) - 8, 0) }}
                        role="status"
                    >
                        <strong>{formatPoints(shown.dk_points)}<span> FPTS</span></strong>
                        {shown.proj_fpts !== null && shown.proj_fpts !== undefined && (
                            <span className="tooltip-row"><span className="tooltip-key tooltip-key-dot" />Projected {formatPoints(shown.proj_fpts)}</span>
                        )}
                        <span className="tooltip-meta">
                            {weekLabel(shown)} {opponentLabel(shown)}{resultLabel(shown) && ` · ${resultLabel(shown)}`}
                        </span>
                    </div>
                )}
            </div>
        </figure>
    );
}
