import {
    formatMatchup, formatPoints, formatSalary, formatSalaryChange, formatValue,
    gradeTone, initials, injuryLabel,
} from './format';

test('money and points', () => {
    expect(formatSalary(9100)).toBe('$9,100');
    expect(formatSalary(null)).toBe('');
    expect(formatPoints(21.84)).toBe('21.8');
    expect(formatPoints(null)).toBe('–');
    expect(formatValue(2.4)).toBe('2.40x');
});

test('salary changes carry their own sign', () => {
    expect(formatSalaryChange(500)).toBe('+500');
    expect(formatSalaryChange(-1200)).toBe('−1,200');
    expect(formatSalaryChange(0)).toBe('–');
    expect(formatSalaryChange(null)).toBe('');
});

test('matchups read home and away, and stay plain when unknown', () => {
    expect(formatMatchup({ opponent: 'NE', home: true })).toBe('vs NE');
    expect(formatMatchup({ opponent: 'NE', home: false })).toBe('@ NE');
    expect(formatMatchup({ opponent: 'NE', home: null })).toBe('NE');
    expect(formatMatchup({ opponent: null, home: true })).toBe('');
});

test('injury statuses abbreviate, and unknown ones are hidden', () => {
    expect(injuryLabel('Questionable')).toBe('Q');
    expect(injuryLabel('IR')).toBe('IR');
    expect(injuryLabel(null)).toBe('');
});

test('grades map to a tone by letter', () => {
    expect(gradeTone('A+')).toBe('a');
    expect(gradeTone('C-')).toBe('c');
    expect(gradeTone(null)).toBe('d');
});

test('initials skip suffixes', () => {
    expect(initials('Patrick Mahomes II')).toBe('PM');
    expect(initials('Kenneth Walker III')).toBe('KW');
    expect(initials('Amon-Ra St. Brown')).toBe('AS');
});
