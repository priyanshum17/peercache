# Peercache

> **Ultra‑light, peer‑to‑peer Memcached laboratory – built for graduate‑level systems research, rapid hypothesis testing, and pedagogy.**

---

## 1 Extended Abstract

Distributed caching has become a first‑class citizen in modern cloud stacks yet remains surprisingly under‑tooled for *micro‑scale experimentation*.  Peercache fills this gap by stitching together commodity **Memcached 1.6** daemons into a fully scriptable **“laptop cluster.”**  By marrying a tiny Python control plane (≈700 SLOC) with deterministic workload generation, the framework allows researchers to explore questions such as:

* How does eviction rate evolve under Zipfian versus uniform access?
* What is the latency penalty of adding a second replica when link RTT varies?
* At what point does socket churn dominate throughput, and how do *thread‑local* clients mitigate it?

Every run is self‑documenting: inputs, topology and performance metrics are persisted as JSON; visual summaries are rendered as PNG; and the entire state tree is amenable to `git add -p`.  Consequently, Peercache supports the full **scientific feedback loop** – design ➝ measure ➝ iterate – with reproducibility baked in.

---

## 2 Contributions

1. **Process‑per‑peer model** mimics real‑world failure modes (crash, slow node, port conflict) while keeping orchestration trivial.
2. **Deterministic consistent‑hash implementation** (32‑bit MD5 slice) enabling direct comparison across runs.
3. **Seven‑parameter workload generator** delivering a continuum of read/write mixes, object sizes and temporal locality.
4. **Zero‑footprint connection reuse** strategy: worst‑case fd cost ≤ *T*×*P*.
5. **Turn‑key plotting pipeline** – one command yields five publication‑ready figures.

---

## 3 Feature Matrix

| Domain                   | Capability                                             | Why it matters                                    |
| ------------------------ | ------------------------------------------------------ | ------------------------------------------------- |
| **CLI**                  | Typer verbs, coloured help, bash completion            | Low cognitive overhead for exploratory work       |
| **Topology persistence** | JSON manifests in `state/peer` & `state/network`       | Crash‑safe; inspectable under version control     |
| **Hash ring**            | Virtual nodes, adjustable replication                  | Study data placement & hot‑spot resilience        |
| **Metrics**              | µ‑latency, p95, throughput, hit %, evictions, RSS      | Covers tail‑latency and capacity planning angles  |
| **Artefacts**            | `results/simulations/` (JSON) + `results/plots/` (PNG) | Long‑term provenance and quick charts             |
| **Notebook**             | *testing.ipynb* with pandas + seaborn templates        | Interactive deep‑dives & paper figure prototyping |

---

## 4 Installation Cheat‑Sheet

Full OS‑specific guide lives in **docs/INSTALLATION.md**.

```bash
git clone https://github.com/your‑org/peercache && cd peercache
./setup.sh                 # creates .venv, resolves locked deps
brew install memcached      # macOS example; use apt/pacman on Linux
```

> **Note:** Large fan‑out tests may require `ulimit ‑n 4096`.

---

## 5 Command Taxonomy & Examples

```text
python main.py <verb> [flags]
│
├─ manager   # global operations
│   ├─ --show               # list networks
│   ├─ --create <name>      
│   └─ --delete <name>
│
├─ network <name>           # per‑network
│   ├─ --show               # stats snapshot
│   ├─ --add <peer_id>
│   └─ --remove <peer_id>
│
└─ peer                     # per‑daemon
    ├─ --start <id>         # alloc port, launch memcached
    ├─ --stop  <id>
    └─ --status             # list live peers
```

<details>
<summary>End‑to‑end demo</summary>

```bash
# 1 – peers
python main.py peer --start p0 --start p1 --start p2 --start p3

# 2 – replicate = 2 ring with 100 virtual nodes
python main.py manager --create exp1
for p in p0 p1 p2 p3; do python main.py network exp1 --add $p; done

# 3 – synthetic workload (see Section 7)
python -m testing.benchmark --name exp1 --peers 4 --scenarios "(4,500) (8,1000)" 

# 4 – explore outputs interactively
jupyter lab testing.ipynb
```

</details>

---

## 6 System Diagram (one‑liner)

```text
CLI ➝ Parser layer (Peer/Network/Registry) ➝ ConsistentHashRing ➝ Memcached
```

A full deep dive, including Mermaid sequence diagram, lives in **docs/ARCHITECTURE.md**.

---

## 7 Benchmark Harness – **`run_benchmark()` Deep Dive**

### 7.1 Parameter Reference

| Name            | Type        | Default       | Semantics                                                      | Impact of ↑                                                               |
| --------------- | ----------- | ------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `name`          | str         | "baseline"    | Run *label* – doubles as network ID and output filename prefix | –                                                                         |
| `peers`         | int         | 8             | Number of Memcached daemons to spawn                           | Wider hash ring; more aggregate RAM; potentially higher coordination cost |
| `memory_mb`     | int         | 32            | Per‑peer memory cap passed via `memcached ‑m`                  | Determines eviction pressure & LRU churn                                  |
| `value_size`    | int         | 16 384        | Raw bytes per SET (hex‑encoded)                                | Larger objects amplify bandwidth & memory utilisation                     |
| `ghost_ratio`   | float       | 0.15          | Probability of a read for a *never‑written* key                | Lowers hit %, accentuates backend latency                                 |
| `ttl_ratio`     | float       | 0.25          | Fraction of writes with `expire=2 s`                           | Models volatile workloads; triggers evictions                             |
| `scenarios`     | list(tuple) | \[(2,400), …] | Each tuple = (*threads*, *reqs* per thread)                    | Stress curve; influences queueing delay & fd count                        |
| `seed`          | int         | 42            | RNG seed applied to Python `random`                            | Full determinism across OS/                                               |
| Python versions |             |               |                                                                |                                                                           |
| `plot`          | bool        | True          | Emit five PNGs under `results/plots`                           | Disable for headless CI                                                   |

### 7.2 Workload Phases

1. **Warm‑Up** – Each thread issues `reqs` SETs to fully populate its keyspace slice; ensures subsequent READs have something to hit.
2. **Mixed Phase** – For every operation:

   * 80 % READ vs. 20 % WRITE.
   * Within READ, `ghost_ratio` controls miss injections.
   * Within WRITE, `ttl_ratio` controls “short‑lived” items via Memcached TTL.
3. **Cool‑Down** – 2.5 s sleep after each stage to let TTL expirations fire, mirroring real workloads with duty cycles.

### 7.3 Metrics Explained

* **`thr`** – Throughput (ops/s) = (workers × reqs × 2) / duration.
* **`lat_avg`, `lat_p95`** – Microsecond latency from Python call to response.
* **`hit_rate`** – Hits / (Hits + Misses) across all peers.
* **`evictions`** – Sum of `evictions` stat from each daemon.
* **`bytes`** – Resident item bytes; helpful for memory leak detection.

### 7.4 Plot Inventory

1. *Throughput vs. concurrency*  ↗︎
2. *Latency (avg & p95)*         ↗︎
3. *Hit/Miss ratio stacked bar* ↗︎
4. *Evictions absolute*          ↗︎
5. *Resident bytes*              ↗︎

Each is saved with prefix `<name>_<metric>.png` for drop‑in use in LaTeX.

---

## 8 Notebook‑Driven Analysis (`testing.ipynb`)

The companion notebook walks through:

* Loading any `results/simulations/*.json` into pandas.
* Re‑computing **CDFs** & **time‑series** latency traces.
* Correlating eviction spikes with TTL burst.
* Generating **publication figures** (violin, violin+strip, boxen) via seaborn.

Running *nbconvert* produces a static PDF suitable for supplemental material.

---

## 9 Experimental Best Practices

1. **Isolate cores** – use `taskset` or `cpuset` so peers don’t steal CPU from workload threads.
2. **Pin clock** – ensure NTP sync and turbo boost policies are logged for fair cross‑machine comparison.
3. **Repeat >5×** – the harness is fast; amortise variance by running each scenario multiple times and use `scipy.stats` to report 95 % CIs.
4. **Check FD ceiling** – kernel default (256) is too low for 16 threads × 32 peers.

---

## 10 Reproducibility Ledger

| Category     | Mechanism                            | File artefact                                        |
| ------------ | ------------------------------------ | ---------------------------------------------------- |
| Source       | SHA‑1 of repo head                   | `results/simulations/*/config.git_sha` (future work) |
| Python deps  | Frozen `requirements.txt`            | tracked in repo                                      |
| Native deps  | `memcached -v` captured in each JSON |  automatic                                           |
| Host info    | `uname -a`, `lscpu`, `ulimit -n`     | notebook cell                                        |
| Random seeds | Single integer in config             | passed through deep call chain                       |

---

## 11 Directory Map (expanded)

```
state/
├── peer/             # pID.json + registry.json
├── network/          # per‑network manifests
└── stats/            # historical artefacts (legacy – moved to results/)

results/
├── simulations/      # run‑level JSON snapshots
└── plots/            # PNG charts (1‑to‑1 with JSON)

docs/                 # architecture, install, usage, etc.

peercache/
├── core/             # hashing only – no external deps
├── parser/           # first‑class domain objects
└── settings/         # pydantic‑powered config loader
```

---

## 12 Roadmap & Open Questions

* **Pluggable cache back‑end** – Redis, Dragonfly, NVMe LSM cache.
* **Fault injection** – network partitions, latency jitter, SIGSTOP peers.
* **Hierarchical rings** – multi‑tier consistent hashing for edge/cloud.
* **Live Prometheus exporter** – scrape every peer + ring health.

---

