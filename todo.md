# To-do

As of 2026-10-12. The issues have the detail; this is the order.

## Now

- [ ] Merge the open PRs: #55 first (your stack already runs it), then #56 and #58, then #57. #57 conflicts with #55 on one README paragraph; resolve that when you get to it.
- [ ] Close #40 and #41: the accuracy page shipped in #49, last week's review in #53.
- [ ] After Monday night's game, review week 5, the first live week: the Lineups review and our model's live accuracy.
- [ ] Decide on a Tuesday model run (about 10:15 AM ET, after the new week's salaries), so our projections are there Tuesday instead of Wednesday.

## Next: tournaments (#51, then #6)

Tournaments pay only the top finishers, so a lineup's ceiling matters more than its average.

- [ ] #51 Each player's range of outcomes, including boom and bust. Compare three ways in the backtest:
  - our projection plus the typical miss for its position and size (the bar to beat)
  - a model of the range (percentiles, or a spread around our projection)
  - logistic classifiers for each threshold

  Score them on P(≥ 20 points), P(≥ 4× salary) and boom/bust around the projection, using probability-accuracy scores (Brier score, log loss) and calibration.
- [ ] #6 Simulate lineups from those ranges, with teammates who score together (a QB and his receivers), to build tournament lineups: stacking and diverse lineups. Backtest lineups optimized on ceiling against lineups optimized on average, and count how often each clears a high score.
- [ ] Ownership, which matters for tournaments: no licensed source yet.

## Model: play-by-play and FTN (#43)

The model trails FantasyPros mostly on ranking (0.394 against 0.434), less on average miss (5.80 against 5.74). Better data on who's missing won't close the gap: even a version that knew who actually played scores the same. It needs new signal.

- [ ] nflverse play-by-play (back to 1999): red-zone and end-zone opportunities, air yards and depth of target, big-play rates. These help the boom/bust work too: touchdown-dependent players and deep threats are the boom-or-bust ones.
- [ ] FTN charting via nflverse (2022 on, so a shorter history): routes, play action and other charting. Check its license first (no unlicensed data, #48).

## Housekeeping

- [ ] Upgrade to Python 3.12: Python 3.10 stops getting security fixes this month. Covers the Dockerfiles, pins and CI.

## Parked

- [ ] #50 Player prop odds: no monthly feed unless the product can pay for it. The 2024 season we already have stays available for experiments.

## Before anyone else uses the app (#48)

- [ ] #45 Salaries from DraftKings and the schedule from nflverse, not FantasyPros. Players on a reserve list are already projected at 0 from nflverse's weekly rosters (#55); check that FantasyPros' projections get the same treatment once the pool comes from DraftKings.
- [ ] #47 Our own headshots, logos and rankings.
- [ ] #44 Replace FantasyPros' projections in the optimizer, once the live record shows ours are better.

The August notes on optimizer ideas that used to be this file are tracked in #6; the original is in git history (49de9ae).
