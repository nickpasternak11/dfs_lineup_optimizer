import React from 'react';
import { vi } from 'vitest';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import App from './App';
import * as client from './api/client';
import { clearAccuracyCache } from './hooks/useAccuracy';

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
    expect(within(dialog).getByRole('img', { name: /FPTS per game, 2026/ })).toBeInTheDocument();
    // Game log table: newest first, with the opponent and the passing line.
    const rows = within(dialog).getAllByRole('row');
    expect(rows[1]).toHaveTextContent('W3');
    expect(rows[1]).toHaveTextContent('vs MIA');
    expect(rows[3]).toHaveTextContent('334');
    // Week 3 has no projection, so only weeks 1 and 2 count:
    // (35.66 - 22.6 + 18.4 - 21.0) / 2 = +5.2.
    expect(within(dialog).getByText(/beat our projection/)).toHaveTextContent('beat our projection 1 of 2');
    expect(within(dialog).getByText(/\/game/)).toHaveTextContent('avg +5.2/game');
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

test('the matchup ranks the opponent against the position, sorts by it, and shows on the card', async () => {
    client.fetchProjections.mockResolvedValue(POOL.map(p => (
        p.player === 'Bijan Robinson'
            ? { ...p, opponent: 'CLE', opp_fpts_allowed: 17.07, opp_fpts_allowed_rank: 7, opp_games: 3 }
            : p.player === 'Josh Allen'
                ? { ...p, opponent: 'ARI', opp_fpts_allowed: 21.74, opp_fpts_allowed_rank: 27, opp_games: 4 }
                : p
    )));
    await renderApp();

    const tough = within(poolRow('Bijan Robinson')).getByText('7th');
    expect(tough).toHaveClass('matchup-tough');
    expect(tough.closest('.matchup-line'))
        .toHaveAttribute('title', 'CLE allows 17.1 FPTS a game to RBs, the 7th fewest (3 games)');
    expect(within(poolRow('Josh Allen')).getByText('27th')).toHaveClass('matchup-soft');

    // Softest matchups first; players without a rank last.
    fireEvent.click(screen.getByRole('button', { name: /Matchup/ }));
    const names = [...document.querySelectorAll('.pool-table tbody .player-name-button')].map(b => b.textContent);
    expect(names.slice(0, 2)).toEqual(['Josh Allen', 'Bijan Robinson']);

    fireEvent.click(poolRow('Bijan Robinson').querySelector('.matchup-cell'));
    const dialog = await screen.findByRole('dialog', { name: /Bijan Robinson/ });
    expect(within(dialog).getByText('CLE vs RB')).toBeInTheDocument();
    expect(within(dialog).getByText('17.1 a game allowed')).toBeInTheDocument();
});

test('the implied team total shows over the over/under, and on the card', async () => {
    client.fetchProjections.mockResolvedValue(POOL.map(p => (
        p.player === 'Josh Allen'
            ? { ...p, opponent: 'NE', game_total: 49.5, team_spread: -7, implied_total: 28.25 }
            : p
    )));
    await renderApp();

    const total = within(poolRow('Josh Allen')).getByText('28.3').closest('.team-total');
    expect(total).toHaveTextContent('O/U 49.5');
    expect(total).toHaveAttribute('title', 'BUF −7 · O/U 49.5 · implied BUF 28.3, NE 21.3');
    // No lines yet: a dash.
    expect(within(poolRow('Bijan Robinson')).queryByText(/O\/U/)).not.toBeInTheDocument();

    client.fetchPlayerGameLog.mockResolvedValue(ALLEN_LOG);
    fireEvent.click(poolRow('Josh Allen').querySelector('.matchup-cell'));
    const dialog = await screen.findByRole('dialog', { name: /Josh Allen/ });
    expect(within(dialog).getByText('Total')).toBeInTheDocument();
    expect(within(dialog).getByText('O/U 49.5 · BUF −7')).toBeInTheDocument();
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

const metrics = (mae, within, rankCorr, bias) => ({ mae, bias, rmse: mae * 1.3, within, rank_corr: rankCorr });
const cell = (n, proj, recent) => ({ player_weeks: n, metrics: { projection: proj, recent_avg: recent } });
const ACCURACY = {
    view: 'history',
    seasons: [2025, 2024],
    first_week: { year: 2024, week: 3 },
    model_versions: [],
    sources: [
        { key: 'projection', label: 'FantasyPros', description: 'FantasyPros' },
        { key: 'recent_avg', label: 'Recent avg', description: 'The Avg column' },
    ],
    year: null,
    position: null,
    min_proj: 5,
    coverage: { considered: 120, scored: 110, no_stats: 8, unlinked: 2, no_baseline: 10, evaluated: 100 },
    summary: cell(100, metrics(5.84, 0.534, 0.413, 0.434), metrics(6.64, 0.482, 0.265, -0.167)),
    by_position: [
        { position: 'QB', ...cell(40, metrics(6.5, 0.47, 0.31, 1.3), metrics(7.4, 0.42, 0.19, 0.1)) },
        { position: 'RB', ...cell(60, metrics(6.2, 0.52, 0.53, 0.8), metrics(6.8, 0.49, 0.41, -0.2)) },
    ],
    by_week: [
        { year: 2024, week: 3, ...cell(50, metrics(5.5, 0.55, 0.4, 0.3), metrics(6.4, 0.5, 0.3, 0)) },
        { year: 2025, week: 3, ...cell(50, metrics(6.1, 0.52, 0.42, 0.5), metrics(6.9, 0.46, 0.23, -0.3)) },
    ],
    by_salary: [
        { low: 4000, high: 6000, ...cell(100, metrics(5.8, 0.53, null, 0.4), metrics(6.6, 0.48, null, -0.2)) },
    ],
    calibration: {
        projection: [{ low: 10, high: 15, player_weeks: 60, predicted: 12.4, actual: 12.5 }],
        recent_avg: [{ low: 10, high: 15, player_weeks: 55, predicted: 12.1, actual: 11.2 }],
    },
};

describe('accuracy page', () => {
    beforeEach(() => {
        clearAccuracyCache();
        client.fetchAccuracy.mockResolvedValue(ACCURACY);
        window.location.hash = '#/accuracy';
    });
    afterEach(() => {
        window.location.hash = '';
    });

    test('compares the projection with the baseline', async () => {
        render(<App />);
        expect(await screen.findByRole('heading', { name: 'Projection accuracy' })).toBeInTheDocument();
        expect(client.fetchAccuracy).toHaveBeenCalledWith({ view: 'history', year: null, position: null, minProj: 5 });
        // The lineups page's slate picker isn't shown here.
        expect(screen.queryByLabelText('Week')).not.toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Accuracy' })).toHaveAttribute('aria-current', 'page');

        const miss = screen.getByText('Average miss', { selector: '.stat-label' }).closest('.accuracy-tile');
        expect(miss).toHaveTextContent('5.8 FPTS');
        expect(miss).toHaveTextContent('Recent avg 6.6 · ▲ 0.8 FPTS better');
        expect(screen.getByText('Players beat it by 0.4 FPTS on average')).toBeInTheDocument();
        expect(screen.getByText(/100 player-weeks with a final game since 2024/)).toHaveTextContent(
            'Not compared: 8 inactive, 2 not matched to NFL stats, 10 with no recent games to average.',
        );

        // By position: the better value of each pair is bold.
        const qb = screen.getByRole('rowheader', { name: 'QB' }).closest('tr');
        expect(within(qb).getByText('6.5')).toHaveClass('is-better');
        expect(within(qb).getByText('7.4')).not.toHaveClass('is-better');
        // Salary tiers have no ranking column.
        const salary = screen.getByRole('table', { name: 'By salary' });
        expect(within(salary).queryByText('Ranking')).not.toBeInTheDocument();
        expect(within(salary).getByRole('rowheader', { name: '$4,000–$5,900' })).toBeInTheDocument();
    });

    test('filters reload the report', async () => {
        render(<App />);
        await screen.findByRole('heading', { name: 'Projection accuracy' });

        await act(async () => {
            fireEvent.click(screen.getByRole('button', { name: 'RB' }));
        });
        expect(client.fetchAccuracy).toHaveBeenLastCalledWith({ view: 'history', year: null, position: 'RB', minProj: 5 });

        await act(async () => {
            fireEvent.change(screen.getByLabelText('Season'), { target: { value: '2024' } });
        });
        expect(client.fetchAccuracy).toHaveBeenLastCalledWith({ view: 'history', year: 2024, position: 'RB', minProj: 5 });
    });

    test('the week chart reads out each week from the keyboard', async () => {
        render(<App />);
        const chart = await screen.findByRole('group', { name: /Average miss by week, 2024 W3 to 2025 W3/ });

        fireEvent.focus(chart);
        expect(within(chart).getByRole('status')).toHaveTextContent('2025 W3');
        fireEvent.keyDown(chart, { key: 'ArrowLeft' });
        expect(within(chart).getByRole('status')).toHaveTextContent('2024 W3FantasyPros 5.5Recent avg 6.450 player-weeks');
    });

    test('the live view leads with our model and resets the season', async () => {
        const live = {
            ...ACCURACY,
            view: 'live',
            seasons: [2026],
            first_week: { year: 2026, week: 5 },
            model_versions: ['1'],
            coverage: { ...ACCURACY.coverage, evaluated: 80 },
            sources: [
                { key: 'model', label: 'Our model', description: 'Ours' },
                ...ACCURACY.sources,
            ],
            summary: {
                player_weeks: 80,
                metrics: {
                    model: metrics(5.6, 0.55, 0.42, 0.1),
                    projection: metrics(5.9, 0.52, 0.44, 0.5),
                    recent_avg: metrics(6.7, 0.47, 0.27, -0.1),
                },
            },
        };
        client.fetchAccuracy.mockImplementation(async ({ view }) => (view === 'live' ? live : ACCURACY));
        render(<App />);
        await screen.findByRole('heading', { name: 'Projection accuracy' });
        await act(async () => {
            fireEvent.change(screen.getByLabelText('Season'), { target: { value: '2024' } });
        });

        await act(async () => {
            fireEvent.click(screen.getByRole('button', { name: 'Live: our model' }));
        });

        expect(client.fetchAccuracy).toHaveBeenLastCalledWith({ view: 'live', year: null, position: null, minProj: 5 });
        const miss = screen.getByText('Average miss', { selector: '.stat-label' }).closest('.accuracy-tile');
        expect(miss).toHaveTextContent('5.6 FPTS');
        expect(miss).toHaveTextContent('FantasyPros 5.9 · ▲ 0.3 FPTS better');
        expect(miss).toHaveTextContent('Recent avg 6.7 · ▲ 1.1 FPTS better');
        expect(screen.getByText(/80 player-weeks with a final game since 2026 week 5/)).toBeInTheDocument();
        expect(screen.getByText(/Version 1 doesn.t know who.s inactive yet/)).toBeInTheDocument();
    });

    test('the live view says when there is no record yet', async () => {
        const empty = { ...ACCURACY, view: 'live', seasons: [], first_week: null, summary: { player_weeks: 0, metrics: {} } };
        client.fetchAccuracy.mockImplementation(async ({ view }) => (view === 'live' ? empty : ACCURACY));
        render(<App />);
        await screen.findByRole('heading', { name: 'Projection accuracy' });
        await act(async () => {
            fireEvent.click(screen.getByRole('button', { name: 'Live: our model' }));
        });
        expect(screen.getByText(/No live record yet/)).toBeInTheDocument();
        expect(screen.queryByText('No finished games match these filters yet.')).not.toBeInTheDocument();
    });

    const reviewPlayer = (name, actual) => ({
        slot: 0, player: name, position: 'WR', team: 'BUF', salary: 5000, projection: 10, actual,
    });
    const REVIEW = {
        weeks: [{ year: 2026, week: 6 }, { year: 2026, week: 5 }],
        year: 2026,
        week: 6,
        saved_at: '2026-10-11T13:00:00Z',
        swapped_at: null,
        complete: true,
        lineups: [
            { phase: 'initial', source: 'fantasypros', strategy: 'projection', projected: 128.5, actual: 117.0, players: [reviewPlayer('Puka Nacua', 21.4)] },
            { phase: 'initial', source: 'model', strategy: 'projection', projected: 131.2, actual: 135.0, players: [reviewPlayer('Jahmyr Gibbs', null)] },
        ],
        best: { actual: 180.0, players: [reviewPlayer('Ja\'Marr Chase', 38.0)] },
        season: [
            { week: 5, complete: true, best: 170.0, lineups: [
                { phase: 'initial', source: 'fantasypros', strategy: 'projection', projected: 125, actual: 121.0 },
                { phase: 'initial', source: 'model', strategy: 'projection', projected: 129, actual: 125.0 },
            ] },
            { week: 6, complete: true, best: 180.0, lineups: [
                { phase: 'initial', source: 'fantasypros', strategy: 'projection', projected: 128.5, actual: 117.0 },
                { phase: 'initial', source: 'model', strategy: 'projection', projected: 131.2, actual: 135.0 },
            ] },
        ],
    };

    test('the lineups view scores the saved lineups against the best possible', async () => {
        client.fetchLineupReview.mockResolvedValue(REVIEW);
        render(<App />);
        await screen.findByRole('heading', { name: 'Projection accuracy' });
        const accuracyCalls = client.fetchAccuracy.mock.calls.length;

        await act(async () => {
            fireEvent.click(screen.getByRole('button', { name: 'Lineups' }));
        });

        expect(client.fetchLineupReview).toHaveBeenCalledWith({ year: null, week: null });
        expect(client.fetchAccuracy.mock.calls.length).toBe(accuracyCalls);
        expect(screen.getByText(/Saved Sun, Oct 11, 9:00 AM ET, before the week.s first game/)).toBeInTheDocument();
        const model = screen.getByRole('rowheader', { name: 'Our model · Projection' }).closest('tr');
        expect(model).toHaveTextContent('131.2135.075%');
        expect(screen.getByRole('rowheader', { name: 'Best possible, in hindsight' }).closest('tr')).toHaveTextContent('180.0100%');
        // The season table averages each lineup over its weeks.
        const season = screen.getByRole('table', { name: '2026 season: actual points, as played' });
        expect(within(season).getByRole('rowheader', { name: 'Average' }).closest('tr')).toHaveTextContent('119.0130.0175.0');

        await act(async () => {
            fireEvent.change(screen.getByLabelText('Week'), { target: { value: '2026-5' } });
        });
        expect(client.fetchLineupReview).toHaveBeenLastCalledWith({ year: 2026, week: 5 });
    });

    test('saved rosters list players in DraftKings slot order, like the optimizer', async () => {
        const player = (name, position, projection) => ({
            slot: 0, player: name, position, team: 'BUF', salary: 5000, projection, actual: 10,
        });
        // Saved in no particular order; the fourth WR is the FLEX.
        const players = [
            player('Bills', 'DST', 8), player('Wide Four', 'WR', 9), player('Tight End', 'TE', 10),
            player('Wide One', 'WR', 20), player('Back Two', 'RB', 14), player('Quarterback', 'QB', 22),
            player('Wide Three', 'WR', 12), player('Back One', 'RB', 18), player('Wide Two', 'WR', 15),
        ];
        client.fetchLineupReview.mockResolvedValue({
            ...REVIEW,
            lineups: [{ phase: 'initial', source: 'model', strategy: 'projection', projected: 128, actual: 90, players }],
            best: null,
        });
        render(<App />);
        await screen.findByRole('heading', { name: 'Projection accuracy' });
        await act(async () => {
            fireEvent.click(screen.getByRole('button', { name: 'Lineups' }));
        });

        const roster = screen.getByRole('rowheader', { name: 'Quarterback' }).closest('table');
        const rows = within(roster).getAllByRole('row').slice(1);
        expect(rows.map(row => within(row).getByRole('rowheader').textContent)).toEqual([
            'Quarterback', 'Back One', 'Back Two', 'Wide One', 'Wide Two', 'Wide Three', 'Tight End', 'Wide Four', 'Bills',
        ]);
        expect(rows.map(row => row.querySelector('.pos-badge').textContent)).toEqual([
            'QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX', 'DST',
        ]);
    });

    test('a Sunday late swap shows beside the lineup it swapped', async () => {
        const swap = (actual, name) => ({
            phase: 'late_swap', source: 'model', strategy: 'projection', projected: 133.0, actual, players: [reviewPlayer(name, 30.0)],
        });
        client.fetchLineupReview.mockResolvedValue({
            ...REVIEW,
            swapped_at: '2026-10-11T15:50:00Z',
            lineups: [...REVIEW.lineups, swap(141.5, 'Kyren Williams')],
            season: [{ ...REVIEW.season[1], lineups: [...REVIEW.season[1].lineups, { ...swap(141.5, 'x'), players: undefined }] }, REVIEW.season[0]],
        });
        render(<App />);
        await screen.findByRole('heading', { name: 'Projection accuracy' });
        await act(async () => {
            fireEvent.click(screen.getByRole('button', { name: 'Lineups' }));
        });

        expect(screen.getByText(/swapped Sun, Oct 11, 11:50 AM ET/)).toBeInTheDocument();
        const model = screen.getByRole('rowheader', { name: 'Our model · Projection' }).closest('tr');
        // Before swaps 135.0, after 141.5 (+6.5), 79% of the best 180.
        expect(model).toHaveTextContent('131.2135.0141.5 (+6.5)79%');
        // FantasyPros wasn't swapped: its "after" cell is empty, its share uses the original.
        expect(screen.getByRole('rowheader', { name: 'FantasyPros · Projection' }).closest('tr')).toHaveTextContent('117.0–65%');
        expect(screen.getByText(/Our model · Projection, after Sunday swaps: 141.5 actual/)).toBeInTheDocument();
    });

    test('the lineups view before any are saved', async () => {
        client.fetchLineupReview.mockResolvedValue({ ...REVIEW, weeks: [], lineups: [], best: null, season: [] });
        render(<App />);
        await screen.findByRole('heading', { name: 'Projection accuracy' });
        await act(async () => {
            fireEvent.click(screen.getByRole('button', { name: 'Lineups' }));
        });
        expect(screen.getByText(/No saved lineups yet/)).toBeInTheDocument();
    });

    test('the header links switch pages', async () => {
        render(<App />);
        await screen.findByRole('heading', { name: 'Projection accuracy' });
        await act(async () => {
            window.location.hash = '#/';
            window.dispatchEvent(new HashChangeEvent('hashchange'));
        });
        expect(await screen.findByText('Suggested lineups')).toBeInTheDocument();
    });
});
