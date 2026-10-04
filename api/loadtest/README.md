# API Load Test

`loadtest.py` is a small closed-loop load generator (httpx + asyncio). Each virtual user sends one request at a time, with no think time, picked at random from a mix that mirrors the frontend:

| Weight | Request |
|---|---|
| 1 | `GET /projections/current_year` |
| 1 | `GET /projections/current_week` |
| 1 | `POST /projections` for 2025 week 3 |
| 1 | `POST /projections` for the current week (year and week omitted) |
| 2 | `POST /optimize` for 2025 week 3 with one QB stack |
| 2 | `POST /optimize` for the current week, started players allowed |

Every request is a read; the test never writes to the database. A warm-up pass runs each request once before measuring, and each concurrency level then runs for 30 seconds. The table it prints reports throughput, latency percentiles over all requests and over optimize alone, and non-200 responses.

## Running it

```bash
make load-test                                              # against the stack's dfs-api
make load-test ARGS="--concurrency 1 5 --duration 10"       # shorter run
make load-test LOAD_TEST_URL=http://dfs-api-other:8080      # another container on the network
```

The target runs the script in a throwaway `python:3.10-slim` container on `dfs_optimizer_network`, so httpx stays out of the API image. To compare two builds on the same machine and data, build each under its own tag, start it on the network with the stack's `.env`, and point `LOAD_TEST_URL` at it:

```bash
docker build -q --target service -f api/Dockerfile -t dfs-api-candidate .
docker run --rm -d --name dfs-api-candidate --network dfs_optimizer_network \
    --env-file .env -e POSTGRES_HOST=dfs-postgres -e API_WORKERS=4 dfs-api-candidate
make load-test LOAD_TEST_URL=http://dfs-api-candidate:8080
docker stop dfs-api-candidate
```

Run one level at a time against one API container; the client and server share the host's CPUs.

## Results

Measured 2026-10-03 on a 28-core WSL2 host (`nproc` = 28, 31 GB RAM), Postgres 16 with the production data (2025 week 3: 491 players; current week 2026 week 4: 487). Latencies in ms.

| Step | Workers | Users | req/s | p50 | p95 | p99 | optimize p50 | optimize p95 | optimize p99 |
|---|---|---|---|---|---|---|---|---|---|
| Baseline (develop) | 1 | 1 | 3.3 | 227 | 771 | 862 | 270 | 792 | 862 |
| | 1 | 5 | 4.5 | 714 | 3074 | 3291 | 1778 | 3218 | 3291 |
| | 1 | 20 | 4.3 | 3289 | 10019 | 11234 | 7432 | 10974 | 11487 |
| | 1 | 50 | 4.1 | 12033 | 20507 | 21883 | 16434 | 21523 | 22259 |
| 2. uvicorn workers | 4 | 1 | 3.4 | 226 | 729 | 752 | 237 | 736 | 752 |
| | 4 | 5 | 8.2 | 431 | 1793 | 2287 | 894 | 2018 | 2345 |
| | 4 | 20 | 8.2 | 928 | 9020 | 9472 | 1817 | 9238 | 9557 |
| | 4 | 50 | 12.2 | 1305 | 17956 | 22435 | 2885 | 20175 | 24711 |
| | 8 | 5 | 14.2 | 246 | 1197 | 1480 | 547 | 1362 | 1545 |
| | 8 | 20 | 13.7 | 670 | 5021 | 6409 | 2290 | 5888 | 6598 |
| | 8 | 50 | 13.0 | 979 | 22315 | 28673 | 2045 | 27452 | 30269 |
| 3. + player-pool cache | 1 | 1 | 3.5 | 218 | 730 | 756 | 232 | 752 | 756 |
| | 1 | 5 | 4.7 | 753 | 3095 | 3390 | 1888 | 3229 | 3390 |
| | 1 | 20 | 4.3 | 3669 | 11919 | 12814 | 7389 | 12499 | 12814 |
| | 4 | 5 | 8.6 | 353 | 1800 | 2157 | 842 | 2069 | 2205 |
| | 4 | 20 | 7.3 | 727 | 10734 | 11731 | 4776 | 11345 | 12047 |
| | 4 | 50 | 11.1 | 1096 | 19599 | 26164 | 4407 | 25309 | 26300 |
| 4. + faster model building | 1 | 1 | 15.8 | 97 | 129 | 156 | 118 | 141 | 179 |
| | 1 | 5 | 32.7 | 180 | 354 | 430 | 264 | 390 | 464 |
| | 1 | 20 | 32.4 | 368 | 1273 | 1455 | 1055 | 1346 | 1482 |
| | 1 | 50 | 32.8 | 1385 | 2726 | 2938 | 2431 | 2815 | 2964 |
| | 4 | 1 | 14.0 | 96 | 126 | 134 | 117 | 130 | 139 |
| | 4 | 5 | 54.9 | 112 | 177 | 214 | 144 | 192 | 234 |
| | 4 | 20 | 75.7 | 184 | 1018 | 1130 | 284 | 1079 | 1152 |
| | 4 | 50 | 64.8 | 493 | 2923 | 3335 | 626 | 3120 | 3440 |
| | 8 | 5 | 52.4 | 107 | 203 | 236 | 149 | 220 | 250 |
| | 8 | 20 | 81.0 | 149 | 670 | 786 | 379 | 727 | 832 |
| | 8 | 50 | 73.2 | 309 | 2662 | 2995 | 1093 | 2875 | 3138 |

What each step showed:

- **Baseline.** One process plateaus at ~4 req/s from 5 users up, and every extra user only adds queueing. Optimize took 250 ms unstacked and ~700 ms with QB stacking, single user.
- **Workers.** Roughly doubles to triples throughput, but a single request is no faster, and tails stay long because each keep-alive connection is pinned to one worker.
- **Cache.** No measurable change in throughput: the database was never the bottleneck (the player-pool query is ~15 ms). It does cut Postgres traffic to a few queries per week per worker per five minutes, which matters once workers multiply.
- **Faster model building.** cProfile showed ~85% of an optimize request in pandas `df.loc` scalar lookups while building the PuLP model (~112k of them for a stacked request); the CBC solve was ~25 ms per lineup. Reading columns into lists once made optimize 2–7x faster (stacked requests the most) with identical lineups, and lifted one worker from 4 to 33 req/s. About half of what remains is the CBC subprocess.

`API_WORKERS=auto` (the default) gives one worker per core up to 4, which on this host reaches ~75 req/s; 8 workers add little more. These are closed-loop users with no think time, so 20 of them stand in for far more real users, who pause between clicks.

Not done: caching identical optimize requests. Requests differ by included/excluded players, and results for the current week change as games kick off, so hit rates would be low for ~100 ms saved. A job queue isn't needed either: optimize is now a ~100 ms synchronous call, well under any HTTP timeout. The next limit is CPU, so scaling further means more cores or API replicas, not a queue.
