# To-do

As of 2026-11-12. The issues have the detail; this is the order.

## Now

- [ ] Upgrade to Python 3.12: Python 3.10 stopped getting security fixes in October 2026. Covers the Dockerfiles, pins and CI.
- [ ] Restart Docker when convenient: new Docker networks can't reach their own containers since the WSL kernel update, so `make test-db` times out. The running stack is fine.
- [ ] Merge #62 (the #51 experiment scripts) when ready.

## Model: play-by-play and FTN (#43)

On 2022–2026 our model ranks players at 0.439 against FantasyPros' 0.472 (average miss 5.54 against 5.42), and averaging the two doesn't beat FantasyPros alone: the model is missing information, not flexibility. Training on fewer seasons made it worse (from 2016: 0.434; from 2021: 0.417). The plan, on #43, in order; keep each feature only if the walk-forward backtest improves:

- [ ] nflverse play-by-play (back to 1999): red-zone, end-zone and goal-line opportunities, air yards and depth of target, big-play rates.
- [ ] Bayesian-shrunk rates (empirical Bayes) as features: TD rate, yards per target and per carry, pulled toward the position's average in proportion to how little data a player has.
- [ ] FTN charting via nflverse (2022 on): catchable and contested targets, routes, play action. Check its license first (no unlicensed data, #48).
- [ ] Later, only if a simulator needs better ranges: a full hierarchical Bayesian model.

## Lineups

Settled by the #51 backtests: one lineup per source (FantasyPros, our model, their average), no blends with the recent average, and the rules: QB stacked with a WR/TE, no DST facing your players, no second TE in FLEX. Simulations and outcome distributions didn't beat the most projected lineup.

- [ ] Watch the live record on Accuracy → Lineups: FantasyPros against our model against the average.
- [ ] Ownership, which matters for tournaments: no licensed source yet.

## Backlog

- [ ] #68 Host the app on a small private server for reliable Sundays ($10–15 a month at most).
- [ ] #50 Player prop odds: parked; no monthly feed unless the product can pay for it.

## Before anyone else uses the app (#48)

- [ ] #45 Salaries from DraftKings and the schedule from nflverse, not FantasyPros. Check that FantasyPros' projections get the reserve-list zeroing (#55) once the pool comes from DraftKings.
- [ ] #46 Injury statuses in the app from nflverse, and game-day inactives.
- [ ] #47 Our own headshots, logos and rankings.
- [ ] #44 Replace FantasyPros' projections in the optimizer, once the live record shows ours are better.

The August notes on optimizer ideas that used to be this file are in git history (49de9ae).
