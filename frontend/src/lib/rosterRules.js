import { ROSTER_SIZE, SALARY_CAP } from './constants';

// Whether locking `player` keeps the locked set buildable into a legal
// lineup: under the cap, and within 1 QB, 1 DST, and 2 RB / 3 WR / 1 TE plus
// a single FLEX among them.
export const canLockPlayer = (player, lockedNames, pool) => {
    if (!player) return { allowed: false, reason: 'Player not found.' };
    if (lockedNames.includes(player.player)) return { allowed: true };
    if (lockedNames.length >= ROSTER_SIZE) {
        return { allowed: false, reason: `Lineup is full (${ROSTER_SIZE}/${ROSTER_SIZE} players locked).` };
    }

    const locked = pool.filter(p => lockedNames.includes(p.player));
    const lockedSalary = locked.reduce((sum, p) => sum + (p.salary || 0), 0);
    const salary = player.salary || 0;
    if (lockedSalary + salary > SALARY_CAP) {
        const remaining = SALARY_CAP - lockedSalary;
        return {
            allowed: false,
            reason: `Over the salary cap: $${remaining.toLocaleString()} left, ${player.player} costs $${salary.toLocaleString()}.`,
        };
    }

    const counts = { QB: 0, RB: 0, WR: 0, TE: 0, DST: 0 };
    locked.forEach(p => { if (counts[p.position] !== undefined) counts[p.position] += 1; });
    const flexUsed = Math.max(0, counts.RB - 2) + Math.max(0, counts.WR - 3) + Math.max(0, counts.TE - 1);

    switch (player.position) {
    case 'QB':
        return counts.QB >= 1 ? { allowed: false, reason: 'Only 1 QB fits in a lineup.' } : { allowed: true };
    case 'DST':
        return counts.DST >= 1 ? { allowed: false, reason: 'Only 1 DST fits in a lineup.' } : { allowed: true };
    case 'RB':
        return counts.RB >= 2 && flexUsed >= 1
            ? { allowed: false, reason: 'At most 3 RBs fit (including FLEX).' } : { allowed: true };
    case 'WR':
        return counts.WR >= 3 && flexUsed >= 1
            ? { allowed: false, reason: 'At most 4 WRs fit (including FLEX).' } : { allowed: true };
    case 'TE':
        return counts.TE >= 1 && flexUsed >= 1
            ? { allowed: false, reason: 'At most 2 TEs fit (including FLEX).' } : { allowed: true };
    default:
        return { allowed: true };
    }
};
