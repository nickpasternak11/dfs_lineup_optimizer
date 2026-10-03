"""Closed-loop load test for the DFS API.

Each virtual user sends one request at a time, picked at random from a mix
that mirrors the frontend: a page load fetches the current year, current week
and the player pool, then the user runs the optimizer a couple of times. Every
request is a read; nothing here writes to the database.

    python loadtest.py --base-url http://dfs-api-scaling:8080 \
        --concurrency 1 5 20 50 --duration 30

Prints one row per concurrency level: throughput and latency percentiles
across all requests, plus the optimize-only percentiles, since that is the
expensive endpoint.
"""

import argparse
import asyncio
import random
import time
from collections import defaultdict

import httpx

# (name, method, path, body, weight). Optimize and projections alternate
# between a fixed past week (stable data) and the current week (year/week
# omitted, so the API resolves the latest week itself).
PAST_WEEK = {"year": 2025, "week": 3}
REQUEST_MIX = [
    ("current_year", "GET", "/projections/current_year", None, 1),
    ("current_week", "GET", "/projections/current_week", None, 1),
    ("projections", "POST", "/projections", PAST_WEEK, 1),
    ("projections", "POST", "/projections", {}, 1),
    ("optimize", "POST", "/optimize", {**PAST_WEEK, "stack_qb_count": 1}, 2),
    # Started players allowed so the current week stays solvable mid-slate.
    ("optimize", "POST", "/optimize", {"include_started_players": True}, 2),
]
WEIGHTS = [entry[-1] for entry in REQUEST_MIX]


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(pct / 100 * len(ordered)) - 1))
    return ordered[index]


async def virtual_user(client, deadline, latencies, errors, rng):
    while time.perf_counter() < deadline:
        name, method, path, body, _ = rng.choices(REQUEST_MIX, weights=WEIGHTS)[0]
        started = time.perf_counter()
        try:
            response = await client.request(method, path, json=body)
            ok = response.status_code == 200
        except httpx.HTTPError:
            ok = False
        elapsed = time.perf_counter() - started
        if ok:
            latencies[name].append(elapsed)
        else:
            errors[name] += 1


async def run_level(base_url: str, concurrency: int, duration: float, seed: int):
    latencies: dict[str, list[float]] = defaultdict(list)
    errors: dict[str, int] = defaultdict(int)
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(base_url=base_url, timeout=120, limits=limits) as client:
        started = time.perf_counter()
        deadline = started + duration
        await asyncio.gather(
            *(
                virtual_user(client, deadline, latencies, errors, random.Random(seed + i))
                for i in range(concurrency)
            )
        )
        wall = time.perf_counter() - started
    return latencies, errors, wall


async def warm_up(base_url: str):
    # First requests pay for imports, pool connections and (later) cache
    # fills; keep them out of the measurements.
    async with httpx.AsyncClient(base_url=base_url, timeout=120) as client:
        for _, method, path, body, _ in REQUEST_MIX:
            response = await client.request(method, path, json=body)
            response.raise_for_status()


def ms(seconds: float) -> str:
    return f"{seconds * 1000:.0f}"


async def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 5, 20, 50])
    parser.add_argument("--duration", type=float, default=30, help="seconds per level")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    await warm_up(args.base_url)

    print(
        "| users | req/s | p50 ms | p95 ms | p99 ms | optimize p50 | optimize p95 "
        "| optimize p99 | errors |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    for concurrency in args.concurrency:
        latencies, errors, wall = await run_level(
            args.base_url, concurrency, args.duration, args.seed
        )
        all_latencies = [value for values in latencies.values() for value in values]
        optimize = latencies["optimize"]
        print(
            f"| {concurrency} | {len(all_latencies) / wall:.1f} "
            f"| {ms(percentile(all_latencies, 50))} | {ms(percentile(all_latencies, 95))} "
            f"| {ms(percentile(all_latencies, 99))} | {ms(percentile(optimize, 50))} "
            f"| {ms(percentile(optimize, 95))} | {ms(percentile(optimize, 99))} "
            f"| {sum(errors.values())} |",
            flush=True,
        )


if __name__ == "__main__":
    asyncio.run(main())
