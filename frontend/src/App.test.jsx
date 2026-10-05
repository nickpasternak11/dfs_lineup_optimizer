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
    fp_player_id: null, gsis_id: null, actual_dk_points: null, ...extra,
});

const POOL = [
    player('Josh Allen', 'QB', 'BUF', 7700, 22.6, { gsis_id: '00-0034857' }),
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


const ALLEN_LOG = {
    player: {
        gsis_id: '00-0034857', player: 'Josh Allen', position: 'QB', birthdate: '1996-05-21',
        height: 77, weight: 237, college: 'Wyoming', draft_year: 2018, draft_round: 1, draft_pick: 7,
    },
    games: [1, 2, 3].map(week => ({
        year: 2026, week, season_type: 'REG', team: 'BUF', opponent: ['HOU', 'NYJ', 'MIA'][week - 1],
        home: week !== 2, team_score: 27, opponent_score: 20, dk_points: [35.66, 18.4, 24.1][week - 1],
        proj_fpts: [22.6, 21.0, null][week - 1], salary: 7700, completions: 25, attempts: 36,
        passing_yards: [334, 220, 260][week - 1], passing_tds: 2, interceptions: 0, carries: 6,
        rushing_yards: 40, rushing_tds: 1, targets: 0, receptions: 0, receiving_yards: 0,
        receiving_tds: 0, fumbles_lost: 0,
    })),
};

const poolRow = name => screen.getAllByText(name)
    .map(element => element.closest('tr'))
    .find(row => row && row.closest('.pool-table'));

test('clicking a pool row opens the player with bio, chart and game log', async () => {
    client.fetchPlayerGameLog.mockResolvedValue(ALLEN_LOG);
    await renderApp();

    fireEvent.click(poolRow('Josh Allen').querySelector('.matchup-cell'));

    const dialog = await screen.findByRole('dialog', { name: /Josh Allen/ });
    expect(client.fetchPlayerGameLog).toHaveBeenCalledWith('00-0034857');
    expect(await within(dialog).findByText(/6'5" · 237 lbs · Wyoming · 2018 · Rd 1, #7 overall/)).toBeInTheDocument();
    expect(within(dialog).getByRole('img', { name: /DraftKings points per game, 2026/ })).toBeInTheDocument();
    // Game log table: newest first, with the opponent and the passing line.
    const rows = within(dialog).getAllByRole('row');
    expect(rows[1]).toHaveTextContent('W3');
    expect(rows[1]).toHaveTextContent('vs MIA');
    expect(rows[3]).toHaveTextContent('334');
    // (35.66 - 22.6 + 18.4 - 21.0) / 2: week 3 has no projection, so it doesn't count.
    expect(within(dialog).getByText(/vs our projection/)).toHaveTextContent('▲ +5.2 vs our projection');
});

test('Escape closes the player and returns focus to the row', async () => {
    client.fetchPlayerGameLog.mockResolvedValue(ALLEN_LOG);
    await renderApp();
    const nameButton = within(poolRow('Josh Allen')).getByRole('button', { name: 'Josh Allen' });
    nameButton.focus();
    fireEvent.click(nameButton);
    await screen.findByRole('dialog');

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(document.activeElement).toBe(nameButton);
});

test('a player without an nflverse id says so instead of requesting a log', async () => {
    await renderApp();
    fireEvent.click(within(poolRow('Bijan Robinson')).getByRole('button', { name: 'Bijan Robinson' }));
    expect(await screen.findByText(/couldn't be matched to NFL stats/)).toBeInTheDocument();
    expect(client.fetchPlayerGameLog).not.toHaveBeenCalled();
});

test('lock buttons in a row act without opening the player', async () => {
    await renderApp();
    await act(async () => {
        fireEvent.click(within(poolRow('Jahmyr Gibbs')).getByRole('button', { name: 'Lock Jahmyr Gibbs' }));
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

test('the Actual column appears once a week has final scores', async () => {
    await renderApp();
    expect(screen.queryByRole('columnheader', { name: /Actual/ })).not.toBeInTheDocument();
});

test('actual points show beside the projection, marked beat or missed', async () => {
    client.fetchProjections.mockResolvedValue(POOL.map(p => (
        p.player === 'Josh Allen' ? { ...p, actual_dk_points: 31.4 }
            : p.player === 'Jahmyr Gibbs' ? { ...p, actual_dk_points: 12.0 } : p
    )));
    await renderApp();

    expect(screen.getByRole('columnheader', { name: /Actual/ })).toBeInTheDocument();
    expect(within(poolRow('Josh Allen')).getByText('31.4')).toHaveClass('actual-beat');
    expect(within(poolRow('Jahmyr Gibbs')).getByText('12.0')).toHaveClass('actual-missed');
});

test('a past week counts every game: players stay available and the optimizer includes them', async () => {
    const played = POOL.map(p => ({ ...p, week: 3, kickoff: '2026-09-27T17:00:00+0000' }));
    client.fetchProjections.mockImplementation(async (year, week) => (week === '3' ? played : POOL));
    await renderApp();

    await act(async () => {
        fireEvent.change(screen.getByLabelText('Week'), { target: { value: '3' } });
    });

    expect(poolRow('Bijan Robinson')).toBeTruthy();
    const lastCall = client.fetchLineups.mock.calls[client.fetchLineups.mock.calls.length - 1][0];
    expect(lastCall).toMatchObject({ week: '3', includeStarted: true });
    expect(screen.getByRole('switch', { name: /Include started games/ })).toBeDisabled();
});
