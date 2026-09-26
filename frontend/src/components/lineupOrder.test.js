import { orderLineup } from './lineupOrder';

const player = (name, position, projFpts) => ({ player: name, position, proj_fpts: projFpts });

// Deliberately shuffled, the way the API returns it.
const lineup = [
    player('Denver Broncos', 'DST', 6.5),
    player('Brock Purdy', 'QB', 22),
    player('Jahmyr Gibbs', 'RB', 26.5),
    player('Kenneth Walker III', 'RB', 21.1),
    player('Sam LaPorta', 'TE', 13.3),
    player('Terrance Ferguson', 'TE', 9.7),
    player('Amon-Ra St. Brown', 'WR', 20.9),
    player('Parker Washington', 'WR', 15.3),
    player('Dontayvion Wicks', 'WR', 11.1),
];

test('orders slots QB, RB, RB, WR, WR, WR, TE, FLEX, DST', () => {
    expect(orderLineup(lineup).map(({ slot }) => slot)).toEqual(
        ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX', 'DST'],
    );
});

test('the higher-projected tight end takes TE and the other becomes FLEX', () => {
    const slots = orderLineup(lineup);
    expect(slots[6]).toEqual({ slot: 'TE', player: lineup[4] });
    expect(slots[7]).toEqual({ slot: 'FLEX', player: lineup[5] });
});

test('a third running back goes to FLEX, lowest projection first out', () => {
    const threeBacks = [
        ...lineup.filter(({ player: name }) => name !== 'Terrance Ferguson'),
        player('Backup Back', 'RB', 30),
    ];
    const slots = orderLineup(threeBacks);
    expect(slots.filter(({ slot }) => slot === 'RB').map(({ player: p }) => p.player))
        .toEqual(['Backup Back', 'Jahmyr Gibbs']);
    expect(slots[7]).toEqual({ slot: 'FLEX', player: threeBacks.find(p => p.player === 'Kenneth Walker III') });
});

test('keeps every player exactly once and leaves the input untouched', () => {
    const before = [...lineup];
    const slots = orderLineup(lineup);
    expect(slots).toHaveLength(9);
    expect(new Set(slots.map(({ player: p }) => p.player)).size).toBe(9);
    expect(lineup).toEqual(before);
});
