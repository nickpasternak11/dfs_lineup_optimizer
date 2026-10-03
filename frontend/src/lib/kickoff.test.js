import {
    defaultKickoffCutoff, hasKickoffPassed, parseKickoff, satisfiesKickoffCutoff,
} from './kickoff';

// 2026 week 4, in the API's format. Times are UTC; comments give Eastern.
const THURSDAY_NIGHT = '2026-10-02T00:15:00+0000'; // Thu 8:15 PM
const SUNDAY_EARLY = '2026-10-04T17:00:00+0000'; // Sun 1:00 PM
const SUNDAY_LONDON = '2026-10-04T13:30:00+0000'; // Sun 9:30 AM
const SUNDAY_NIGHT = '2026-10-05T00:20:00+0000'; // Sun 8:20 PM (Monday in UTC)
const MONDAY_NIGHT = '2026-10-06T00:15:00+0000'; // Mon 8:15 PM

test('parses the API format, including offsets without a colon', () => {
    expect(parseKickoff(SUNDAY_EARLY).toISOString()).toBe('2026-10-04T17:00:00.000Z');
    expect(parseKickoff(null)).toBeNull();
    expect(parseKickoff('not a date')).toBeNull();
});

test('a game has kicked off once its start time is reached', () => {
    const now = new Date('2026-10-04T17:00:00Z');
    expect(hasKickoffPassed(SUNDAY_EARLY, now)).toBe(true);
    expect(hasKickoffPassed(SUNDAY_NIGHT, now)).toBe(false);
    // Older weeks have no kickoff and never count as started.
    expect(hasKickoffPassed(null, now)).toBe(false);
});

test.each([
    ['', [THURSDAY_NIGHT, SUNDAY_LONDON, SUNDAY_EARLY, SUNDAY_NIGHT, MONDAY_NIGHT]],
    ['friday', [SUNDAY_LONDON, SUNDAY_EARLY, SUNDAY_NIGHT, MONDAY_NIGHT]],
    ['sunday', [SUNDAY_LONDON, SUNDAY_EARLY, SUNDAY_NIGHT, MONDAY_NIGHT]],
    ['sunday_main', [SUNDAY_EARLY, SUNDAY_NIGHT]],
])('cutoff %p keeps the right games, judged in Eastern time', (cutoff, kept) => {
    const all = [THURSDAY_NIGHT, SUNDAY_LONDON, SUNDAY_EARLY, SUNDAY_NIGHT, MONDAY_NIGHT];
    expect(all.filter(kickoff => satisfiesKickoffCutoff(kickoff, cutoff))).toEqual(kept);
});

test('players without a kickoff pass every cutoff', () => {
    expect(satisfiesKickoffCutoff(null, 'sunday_main')).toBe(true);
});

test('the default cutoff hides games that are usually over by then', () => {
    expect(defaultKickoffCutoff(new Date('2026-10-01T16:00:00Z'))).toBe(''); // Thu
    expect(defaultKickoffCutoff(new Date('2026-10-02T16:00:00Z'))).toBe('friday'); // Fri
    expect(defaultKickoffCutoff(new Date('2026-10-04T16:00:00Z'))).toBe('sunday'); // Sun
    // Saturday 11 PM Eastern is already Sunday in UTC.
    expect(defaultKickoffCutoff(new Date('2026-10-04T03:00:00Z'))).toBe('friday');
});
