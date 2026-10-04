const ROSTER_SLOTS = [['QB', 1], ['RB', 2], ['WR', 3], ['TE', 1]];
const FLEX_POSITIONS = ['RB', 'WR', 'TE'];

// Orders a lineup QB, RB, RB, WR, WR, WR, TE, FLEX, DST. Within a position the
// higher projection fills the base slot, so the extra RB/WR/TE becomes FLEX.
export const orderLineup = (lineup) => {
    const byPosition = {};
    [...lineup]
        .sort((a, b) => b.proj_fpts - a.proj_fpts)
        .forEach(player => {
            (byPosition[player.position] = byPosition[player.position] || []).push(player);
        });

    const slots = [];
    ROSTER_SLOTS.forEach(([position, count]) => {
        (byPosition[position] || []).splice(0, count)
            .forEach(player => slots.push({ slot: position, player }));
    });
    FLEX_POSITIONS.forEach(position => {
        (byPosition[position] || []).splice(0)
            .forEach(player => slots.push({ slot: 'FLEX', player }));
    });
    (byPosition.DST || []).forEach(player => slots.push({ slot: 'DST', player }));
    return slots;
};
