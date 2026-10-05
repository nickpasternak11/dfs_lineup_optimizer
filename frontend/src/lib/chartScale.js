// Clean y-axis bounds and ticks (0 / 10 / 20 ...) covering [min, max].
// The baseline stays at 0 unless a value is negative (a DST can score -4).
export const niceScale = (min, max, targetTicks = 5) => {
    const low = Math.min(0, min);
    const high = Math.max(0, max, 1);
    const rough = (high - low) / targetTicks;
    const magnitude = 10 ** Math.floor(Math.log10(rough));
    const step = [1, 2, 2.5, 5, 10].map(m => m * magnitude).find(s => s >= rough);
    const top = Math.ceil(high / step) * step;
    const bottom = Math.floor(low / step) * step;
    const ticks = [];
    for (let value = bottom; value <= top + step / 2; value += step) {
        ticks.push(Math.round(value * 100) / 100);
    }
    return { min: bottom, max: top, ticks };
};
