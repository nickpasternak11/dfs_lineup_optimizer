const isMissing = value => value === null || value === undefined || value === '';

export const formatSalary = value => (isMissing(value) ? '' : `$${Number(value).toLocaleString()}`);

export const formatPoints = value => (isMissing(value) ? '–' : Number(value).toFixed(1));

export const formatValue = value => (isMissing(value) ? '–' : `${Number(value).toFixed(2)}x`);

export const formatSalaryChange = (value) => {
    if (isMissing(value)) return '';
    const amount = Number(value);
    if (amount === 0) return '–';
    return `${amount > 0 ? '+' : '−'}${Math.abs(amount).toLocaleString()}`;
};

export const isHome = player => [true, 1, '1', 'true', 'h', 'home'].includes(
    typeof player.home === 'string' ? player.home.toLowerCase() : player.home,
);

// "vs NE" at home, "@ NE" away. Older weeks don't record home/away.
export const formatMatchup = (player) => {
    if (!player.opponent) return '';
    if (player.home === null || player.home === undefined) return player.opponent;
    return `${isHome(player) ? 'vs' : '@'} ${player.opponent}`;
};

const INJURY_LABELS = {
    questionable: 'Q', doubtful: 'D', out: 'O', ir: 'IR', pup: 'PUP', suspended: 'SUS',
};

export const injuryLabel = status => INJURY_LABELS[String(status || '').trim().toLowerCase()] || '';

export const gradeTone = (grade) => {
    const letter = String(grade || '').trim().toUpperCase().charAt(0);
    return ['A', 'B', 'C', 'D', 'F'].includes(letter) ? letter.toLowerCase() : 'd';
};

export const initials = name => String(name || '')
    .replace(/\b(Jr|Sr|II|III|IV|V)\b\.?/g, '')
    .split(/\s+/)
    .filter(Boolean)
    .map(part => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
