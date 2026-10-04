import React from 'react';
import { vi } from 'vitest';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import App from './App';
import * as client from './api/client';

vi.mock('./api/client');

const player = (name, position, team, salary, proj, extra = {}) => ({
    year: 2026, week: 4, player: name, position, team, opponent: 'OPP', home: true,
    kickoff: '2099-10-04T17:00:00+0000', grade: 'A', rank: 1, avg_fpts: proj, proj_fpts: proj,
    salary, salary_change: 0, value: proj / (salary / 1000), injury_status: null, injury_type: null,
    fp_player_id: null, ...extra,
});

const POOL = [
    player('Josh Allen', 'QB', 'BUF', 7700, 22.6),
    player('Bijan Robinson', 'RB', 'ATL', 8700, 21.8),
    player('Jahmyr Gibbs', 'RB', 'DET', 9000, 25.6),
    player('Ja\'Marr Chase', 'WR', 'CIN', 8100, 19.9),
    player('CeeDee Lamb', 'WR', 'DAL', 7800, 18.9),
    player('Puka Nacua', 'WR', 'LAR', 7700, 19.1),
    player('Sam LaPorta', 'TE', 'DET', 4100, 11.6),
    player('Jonathan Taylor', 'RB', 'IND', 7600, 18.6),
    player('Minnesota Vikings', 'DST', 'MIN', 3000, 8.0),
    player('Old Timer', 'WR', 'NYJ', 3000, 5.0, { kickoff: '2000-01-01T17:00:00+0000' }),
];
const LINEUP = POOL.filter(p => p.player !== 'Old Timer');

beforeEach(() => {
    client.fetchCurrentSlate.mockResolvedValue({ year: '2026', week: '4' });
    client.fetchProjections.mockResolvedValue(POOL);
    client.fetchLineups.mockResolvedValue([LINEUP, LINEUP, LINEUP]);
    client.errorMessage.mockImplementation((error, fallback) => fallback);
});

const renderApp = async () => {
    render(<App />);
    await screen.findByText('Suggested lineups');
    await screen.findAllByText('Josh Allen');
};

test('loads the current week and shows the pool and lineups', async () => {
    await renderApp();
    expect(client.fetchProjections).toHaveBeenCalledWith('2026', '4');
    expect(screen.getByRole('tab', { name: /Projection/ })).toBeInTheDocument();
    // In the pool table and in the lineup card.
    expect(screen.getAllByText('Josh Allen')).toHaveLength(2);
    // Players whose games have started are under Unavailable, not Available.
    expect(screen.queryByText('Old Timer')).not.toBeInTheDocument();
});

test('locking a player re-runs the optimizer with them included', async () => {
    await renderApp();
    const row = screen.getAllByText('Bijan Robinson')[0].closest('tr');
    await act(async () => {
        fireEvent.click(within(row).getByRole('button', { name: 'Lock Bijan Robinson' }));
    });
    const lastCall = client.fetchLineups.mock.calls[client.fetchLineups.mock.calls.length - 1][0];
    expect(lastCall.locked).toEqual(['Bijan Robinson']);
    expect(screen.getByText(/Locked 1\/9/)).toBeInTheDocument();
});

test('changing the week reloads that slate', async () => {
    await renderApp();
    await act(async () => {
        fireEvent.change(screen.getByLabelText('Week'), { target: { value: '3' } });
    });
    expect(client.fetchProjections).toHaveBeenLastCalledWith('2026', '3');
    expect(screen.getByRole('button', { name: 'Back to this week' })).toBeInTheDocument();
});

test('an optimizer error is shown in place of the lineups', async () => {
    client.fetchLineups.mockRejectedValue(new Error('boom'));
    render(<App />);
    expect(await screen.findByText('No lineups')).toBeInTheDocument();
});
