import json
import os
import random
import signal
import statistics as stats
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Sequence, Tuple

import matplotlib.pyplot as plt

from peercache.parser.manager import NetworkManager
from peercache.parser.network import Network
from peercache.parser.peer import Peer

from pathlib import Path
from datetime import datetime

# ───────────────────────── helpers ────────────────────────── #
def _rand_val(size: int) -> str:
    return os.urandom(size).hex()


def _pct(series: List[float], q: float) -> float:
    if not series:
        return 0.0
    k = int(round(q / 100 * (len(series) - 1)))
    return sorted(series)[k]


# ───────────────────────── workload thread ─────────────────── #
def _one_worker(
    net: Network,
    wid: int,
    reqs: int,
    value_size: int,
    ghost_ratio: float,
    ttl_ratio: float,
) -> Dict[str, List[float]]:
    """
    Warm-up SETs every key, then mixed read/write:
      - 80 % reads, 20 % writes
      - ghost_ratio chance of reading an unknown key
      - ttl_ratio of writes get expire=2 s
    """
    lat: List[float] = []
    hits = misses = writes = 0

    keys = [f"{wid}:{i}" for i in range(reqs)]

    # warm-up
    for k in keys:
        t0 = time.perf_counter_ns()
        net.cache_set(k, _rand_val(value_size))
        lat.append((time.perf_counter_ns() - t0) / 1_000)

    time.sleep(0.05)

    # mixed phase
    for _ in range(reqs):
        if random.random() < 0.8:  # READ
            if random.random() < ghost_ratio:
                k = f"ghost:{random.randint(0, 1_000_000)}"
            else:
                k = random.choice(keys)
            t0 = time.perf_counter_ns()
            res = net.cache_get(k)
            lat.append((time.perf_counter_ns() - t0) / 1_000)
            if res != "MISS":
                hits += 1
            else:
                misses += 1
        else:  # WRITE
            k = random.choice(keys)
            ttl = 2 if random.random() < ttl_ratio else 0
            for pid in net.ring.get_n(k, 1):
                Peer(pid)._client().set(k, _rand_val(value_size), expire=ttl)
            writes += 1

    return {"lat": lat, "hits": [hits], "misses": [misses], "writes": [writes]}


# ───────────────────────── single stage ─────────────────────── #
def _run_stage(
    net: Network,
    workers: int,
    reqs: int,
    value_size: int,
    ghost_ratio: float,
    ttl_ratio: float,
) -> Dict:
    agg = defaultdict(list)
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [
            pool.submit(
                _one_worker, net, w, reqs, value_size, ghost_ratio, ttl_ratio
            )
            for w in range(workers)
        ]
        for f in as_completed(futs):
            part = f.result()
            for k, v in part.items():
                agg[k].extend(v)

    dur = time.perf_counter() - start
    total_ops = workers * reqs * 2
    thr = total_ops / dur

    hits = sum(agg["hits"])
    misses = sum(agg["misses"])
    hit_rate = hits / (hits + misses) if hits + misses else 0.0

    evictions = bytes_used = 0
    for pid in net.peers:
        s = Peer(pid).stats()
        evictions += int(s["evictions"])
        bytes_used += int(s["bytes"])

    return {
        "workers": workers,
        "reqs": reqs,
        "ops": total_ops,
        "dur": dur,
        "thr": thr,
        "lat_avg": stats.mean(agg["lat"]),
        "lat_p95": _pct(agg["lat"], 95),
        "hits": hits,
        "misses": misses,
        "hit_rate": hit_rate,
        "evictions": evictions,
        "bytes": bytes_used,
    }


# ───────────────────────── public API ───────────────────────── #
def run_benchmark(
    *,
    name: str,
    peers: int = 8,
    memory_mb: int = 32,
    value_size: int = 16_384,
    ghost_ratio: float = 0.15,
    ttl_ratio: float = 0.25,
    scenarios: Sequence[Tuple[int, int]] = ((2, 400), (4, 800)),
    seed: int = 42,
    plot: bool = True,
) -> List[Dict]:
    """
    Execute a full ramp test and (optionally) save 5 PNG charts.

    Returns the per-stage result list for programmatic inspection.
    """
    random.seed(seed)

    # --- spin up peers --------------------------------------------------- #
    mgr = NetworkManager()
    mgr.create_network(name)
    net = Network(name)
    peers_list: List[Peer] = []
    for i in range(peers):
        p = Peer(f"{name}_p{i}")
        p.start(memory_mb=memory_mb)
        peers_list.append(p)
        net.add_peer(p.id)

    # --- run workload matrix -------------------------------------------- #
    results = []
    for w, r in scenarios:
        print(f"\n▶ Stage: {w} workers × {r} req")
        res = _run_stage(
            net, w, r, value_size, ghost_ratio, ttl_ratio
        )
        results.append(res)
        print(json.dumps(res, indent=2))
        time.sleep(2.5)  # give TTL items a chance to expire

    # --- visualisation --------------------------------------------------- #
    cfg = dict(
        name=name,
        peers=peers,
        memory_mb=memory_mb,
        value_size=value_size,
        ghost_ratio=ghost_ratio,
        ttl_ratio=ttl_ratio,
        scenarios=list(scenarios),
        seed=seed,
    )
    print(f"\n🔧 Configuration:\n{json.dumps(cfg, indent=2)}")
    if plot:
        _make_plots(results, prefix=name)
    _save_json(cfg, results, prefix=name)

    # --- clean up -------------------------------------------------------- #
    for p in peers_list:
        p.stop()

    return results


def _save_json(config: Dict, stages: List[Dict], prefix: str) -> None:
    """
    Persist run configuration + per-stage results to
    state/stats/<prefix>_<timestamp>.json
    """
    out_dir = Path("results/simulations")
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"{prefix}_{ts}.json"
    print(f"💾 Saving results to → {out_path}")

    payload = {"config": config, "stages": stages}
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"🔖 Results saved → {out_path}")

# ───────────────────────── chart helper ──────────────────────── #
def _make_plots(results: List[Dict], *, prefix: str = "") -> None:
    x = [r["workers"] for r in results]

    def _save(fig, fname):
        out_dir = Path("results/plots")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{prefix}_{fname}.png"
        fig.tight_layout()
        fig.savefig(out_path, dpi=120)
        print(f"🖼️ Saved plot → {out_path}")

    # Throughput
    fig1 = plt.figure()
    plt.plot(x, [r["thr"] for r in results], "o-")
    plt.title("Throughput")
    plt.xlabel("Workers")
    plt.ylabel("Ops/s")
    plt.grid(True)
    _save(fig1, "throughput")

    # Latency
    fig2, ax = plt.subplots()
    ax.plot(x, [r["lat_avg"] for r in results], "o-", label="avg")
    ax.plot(x, [r["lat_p95"] for r in results], "s--", label="p95")
    ax.set_title("Latency")
    ax.set_xlabel("Workers")
    ax.set_ylabel("µs")
    ax.grid(True)
    ax.legend()
    _save(fig2, "latency")

    # Hit / miss %
    fig3 = plt.figure()
    hit_pct = [r["hit_rate"] * 100 for r in results]
    miss_pct = [100 - h for h in hit_pct]
    plt.bar(x, hit_pct, label="Hit %")
    plt.bar(x, miss_pct, bottom=hit_pct, label="Miss %", alpha=0.4)
    plt.title("Hit / Miss rate")
    plt.xlabel("Workers")
    plt.ylabel("%")
    plt.ylim(0, 105)
    plt.grid(axis="y")
    plt.legend()
    _save(fig3, "hit_miss")

    # Evictions
    fig4 = plt.figure()
    plt.plot(x, [r["evictions"] for r in results], "d-", color="tab:red")
    plt.title("Evictions")
    plt.xlabel("Workers")
    plt.ylabel("# evictions")
    plt.grid(True)
    _save(fig4, "evictions")

    fig5 = plt.figure()
    plt.plot(x, [r["bytes"] / 1_048_576 for r in results], "p-")
    plt.title("Bytes in use")
    plt.xlabel("Workers")
    plt.ylabel("MB")
    plt.grid(True)
    _save(fig5, "memory")

    # 1 ─ Latency CDF (per stage)
    fig6 = plt.figure()
    for r in results:
        sorted_lat = sorted(r["lat_dist"]) if "lat_dist" in r else []
        if not sorted_lat:
            continue
        y = [i / len(sorted_lat) * 100 for i in range(len(sorted_lat))]
        plt.plot(sorted_lat, y, label=f'{r["workers"]} workers')
    plt.title("Latency CDF")
    plt.xlabel("µs")
    plt.ylabel("Percentile")
    plt.grid(True)
    plt.legend()
    _save(fig6, "latency_cdf")

    # 3 ─ Throughput vs. Hit-Rate scatter
    fig8 = plt.figure()
    thr = [r["thr"] for r in results]
    hit = [r["hit_rate"] * 100 for r in results]
    plt.scatter(hit, thr)
    plt.title("Throughput vs. Hit Rate")
    plt.xlabel("Hit Rate (%)")
    plt.ylabel("Ops/s")
    plt.grid(True)
    for txt, x, y in zip([r["workers"] for r in results], hit, thr):
        plt.annotate(txt, (x, y))
    _save(fig8, "thr_vs_hit")


    plt.show()