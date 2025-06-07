# Usage & CLI Reference

Peercache ships a Typer‑powered CLI with three top‑level verbs: **manager**, **network**, **peer**.

```text
python main.py [global‑opts] <command> [command‑opts]
```

---

## manager

| Flag              | Description                          |
| ----------------- | ------------------------------------ |
| `--show`          | List all networks                    |
| `--create <name>` | Create a new network                 |
| `--delete <name>` | Delete a network (and its JSON file) |

Example:

```bash
python main.py manager --create staging
```

---

## network

Operate on an **existing** network.

| Arg / Flag        | Description                             |
| ----------------- | --------------------------------------- |
| `<name>`          | Network name                            |
| `--show`          | Display stats (peers, replicas, vnodes) |
| `--add <peer>`    | Attach a peer to ring (auto rebuild)    |
| `--remove <peer>` | Detach a peer                           |

---

## peer

| Flag           | Description                               |
| -------------- | ----------------------------------------- |
| `--start <id>` | Launch new Memcached daemon with given ID |
| `--stop <id>`  | Kill daemon and unregister                |
| `--status`     | Print currently active peers              |

The default port range is **12000 – 29999**; the first free port is picked.

---

## Running Benchmarks

```bash
python -m testing.benchmark \
  --name baseline \
  --peers 8 \
  --memory-mb 32 \
  --scenarios "(2,400) (4,800) (8,200) (16,100)"
```

Outputs:

* JSON ← `results/simulations/<name>_<timestamp>.json`
* Plots ← `results/plots/<metric>.png`

---

## Cleaning Up

Sometimes you want to start fresh:

```bash
pkill -f memcached               # kill stray daemons
rm -rf state/peer/*.json state/network/*.json results/*
```

---

## Advanced Tips

* Benchmarks accept `--value-size`, `--ghost-ratio`, `--ttl-ratio` for stress testing.
* Use `MEMCACHED_PATH=/opt/memcached/bin/memcached` to run a custom build.
* The ring supports **weighted replicas** – set `vnodes` to a multiple of desired weight and add the peer multiple times.

*Happy caching!*
