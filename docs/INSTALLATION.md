# Installation Guide

> Tested on **macOS 14**, **Ubuntu 24.04** and **WSL 2**. Requires Python ≥3.10 and a `memcached` binary ≥1.6.

---

## 1 – Clone & bootstrap

```bash
git clone https://github.com/your‑org/peercache.git
cd peercache
./setup.sh     
```

`setup.sh` is idempotent – rerun any time to upgrade dependencies.

### What setup.sh does

1. Creates a dedicated **virtual environment** at `.venv/`.
2. Installs `pip-tools` and resolves **pinned** versions into `requirements.txt`.
3. Installs the project in **editable** mode: `pip install -e .`.
4. Sets `alias peercache= pyhton3 main.py`.

---

## 2 – Install Memcached

| Platform             | Command                                                   |
| -------------------- | --------------------------------------------------------- |
| **macOS** (Homebrew) | `brew install memcached`                                  |
| **Ubuntu/Debian**    | `sudo apt install memcached libevent-dev`                 |
| **Arch Linux**       | `sudo pacman -S memcached`                                |
| **Docker**           | `docker run --name mc -p 11211:11211 -d memcached:alpine` |

> **Tip:** On macOS you may need to increase the *ulimit* for open files when running very large tests.

---

## 3 – Environment Variables (optional)

| Variable              | Default     | Purpose                            |
| --------------------- | ----------- | ---------------------------------- |
| `PEERCACHE_STATE_DIR` | `./state`   | Root folder for runtime artefacts  |
| `MEMCACHED_PATH`      | `memcached` | Override if binary lives elsewhere |

Export them in your shell or add to `.env`.

---
## 4 – Troubleshooting

| Symptom                                                        | Fix                                                                                        |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `BlockingIOError: [Errno 35] Resource temporarily unavailable` | Increase OS‑wide file‑descriptor limit (`ulimit -n 4096`) or lower `workers` count.        |
| `RuntimeError: Failed to start peer …`                         | Check that no other process is already listening on the chosen port range (12000 – 30000). |
| Plots not saved                                                | Ensure `matplotlib` backend can write PNGs (install `tk` on minimal servers).              |
