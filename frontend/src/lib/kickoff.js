// NFL slates are defined in Eastern time, so the cutoff filters work in ET
// whatever the viewer's own time zone is. Displayed times stay local.
const EASTERN = 'America/New_York';

// The API sends offsets without a colon ("+0000"), which Safari can't parse.
export const parseKickoff = (value) => {
    if (!value) return null;
    const date = new Date(String(value).replace(/([+-]\d{2})(\d{2})$/, '$1:$2'));
    return Number.isNaN(date.getTime()) ? null : date;
};

const easternDayAndHour = (date) => {
    const parts = new Intl.DateTimeFormat('en-US', {
        timeZone: EASTERN, weekday: 'short', hour: 'numeric', hourCycle: 'h23',
    }).formatToParts(date);
    const part = (type) => parts.find(p => p.type === type).value;
    return { day: part('weekday'), hour: Number(part('hour')) % 24 };
};

export const hasKickoffPassed = (value, now = new Date()) => {
    const kickoff = parseKickoff(value);
    return kickoff !== null && kickoff <= now;
};

export const satisfiesKickoffCutoff = (value, cutoff) => {
    const kickoff = parseKickoff(value);
    if (!cutoff || !kickoff) return true;

    const { day, hour } = easternDayAndHour(kickoff);
    if (cutoff === 'friday') return ['Fri', 'Sat', 'Sun', 'Mon'].includes(day);
    if (cutoff === 'sunday') return ['Sun', 'Mon'].includes(day);
    if (cutoff === 'sunday_main') return day === 'Sun' && hour >= 13;
    return true;
};

// Later in the week, the earlier games are usually over: default to hiding them.
export const defaultKickoffCutoff = (now = new Date()) => {
    const { day } = easternDayAndHour(now);
    if (day === 'Fri' || day === 'Sat') return 'friday';
    if (day === 'Sun') return 'sunday';
    return '';
};

export const formatKickoff = (value) => {
    const kickoff = parseKickoff(value);
    if (!kickoff) return '';
    return new Intl.DateTimeFormat('en-US', {
        weekday: 'short', hour: 'numeric', minute: '2-digit',
    }).format(kickoff).replace(',', '');
};
