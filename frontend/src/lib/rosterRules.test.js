import { canLockPlayer } from './rosterRules';

const p = (name, position, salary = 5000) => ({ player: name, position, salary });

const pool = [
    p('QB One', 'QB'), p('QB Two', 'QB'),
    p('RB One', 'RB'), p('RB Two', 'RB'), p('RB Three', 'RB'), p('RB Four', 'RB'),
    p('WR One', 'WR'), p('WR Two', 'WR'), p('WR Three', 'WR'), p('WR Four', 'WR'),
    p('TE One', 'TE'), p('TE Two', 'TE'),
    p('DST One', 'DST'), p('DST Two', 'DST'),
    p('Pricey', 'WR', 45100),
];
const find = name => pool.find(player => player.player === name);

test('an empty lineup accepts anyone', () => {
    expect(canLockPlayer(find('QB One'), [], pool)).toEqual({ allowed: true });
});

test('only one QB and one DST', () => {
    expect(canLockPlayer(find('QB Two'), ['QB One'], pool).allowed).toBe(false);
    expect(canLockPlayer(find('DST Two'), ['DST One'], pool).allowed).toBe(false);
});

test('a third RB takes the FLEX, after which a fourth RB or a fifth WR cannot fit', () => {
    expect(canLockPlayer(find('RB Three'), ['RB One', 'RB Two'], pool).allowed).toBe(true);
    const flexTaken = ['RB One', 'RB Two', 'RB Three', 'WR One', 'WR Two', 'WR Three'];
    expect(canLockPlayer(find('RB Four'), flexTaken, pool).allowed).toBe(false);
    expect(canLockPlayer(find('WR Four'), flexTaken, pool).allowed).toBe(false);
    expect(canLockPlayer(find('TE One'), flexTaken, pool).allowed).toBe(true);
});

test('the salary cap counts locked players', () => {
    const result = canLockPlayer(find('Pricey'), ['QB One'], pool);
    expect(result.allowed).toBe(false);
    expect(result.reason).toMatch(/\$45,000 left/);
});

test('a player who is already locked is always allowed', () => {
    expect(canLockPlayer(find('QB One'), ['QB One'], pool).allowed).toBe(true);
});
