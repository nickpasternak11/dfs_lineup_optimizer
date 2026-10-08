# To-do

As of 2026-10-07. The issues have the detail; this is the order.

## Now

- [ ] Merge and deploy #55 (injury reports, model version 2) before Thursday's 9 AM ET lineup save: `make build`, `make db-upgrade`, `make backfill-game-logs`, `make run`.
- [ ] Close #40 and #41: the accuracy page shipped in #49, last week's review in #53.
- [ ] After Monday night's game, check the first live week (5): the Lineups review and our model's live accuracy.

## Next

- [ ] Upgrade to Python 3.12: Python 3.10 stops getting security fixes this month. Covers the Dockerfiles, pins and CI.
- [ ] Decide on the player-props feed: the $59 one-month backfill (#50).

## Model: beat FantasyPros before replacing it (#44)

The model trails FantasyPros mostly on ranking (0.394 against 0.434), less on average miss (5.80 against 5.74). Better data on who's missing won't close the gap: even a version that knew who actually played scores the same. It needs new signal.

- [ ] #50 Player prop odds, if the feed is bought.
- [ ] #43 FTN charting data, if not. Check its license first (no unlicensed data, #48).
- [ ] #51 Each player's distribution of outcomes, then #6 to use them in the optimizer: simulations, stacking, diverse lineups.

## Before anyone else uses the app (#48)

- [ ] #45 Salaries from DraftKings and the schedule from nflverse, not FantasyPros. Players on a reserve list are already projected at 0 from nflverse's weekly rosters (#55); check that FantasyPros' projections get the same treatment once the pool comes from DraftKings.
- [ ] #47 Our own headshots, logos and rankings.
- [ ] #44 Replace FantasyPros' projections in the optimizer, once the live record shows ours are better.

The August notes on optimizer ideas that used to be this file are tracked in #6; the original is in git history (49de9ae).
