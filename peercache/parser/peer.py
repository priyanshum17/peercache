import json
import socket
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional
import threading
from functools import lru_cache
from pymemcache.client.base import Client

from peercache.settings.settings import SETTINGS
from peercache.parser.registry import add as _reg_add, remove as _reg_rm


class Peer:
    """
    Thin wrapper around a memcached daemon plus a local JSON metadata file.
    """

    def __init__(self, peer_id: str, port: int | None = None):
        self.id = peer_id
        self.port = port if port is not None else self._find_free_port()
        self.path: Path = Path(SETTINGS.PEER_FOLDER_PATH) / f"{self.id}.json"
        self.pid: Optional[int] = None  # populated on start()
        self._load_or_init()

    @staticmethod
    def _find_free_port(min_port: int = 12000, max_port: int = 30000) -> int:
        """Grab an unused TCP port in the given range."""
        for port in range(min_port, max_port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("localhost", port))
                    return port
                except OSError:
                    continue
        raise RuntimeError("No free port available in the safe range.")

    def _load_or_init(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text())
            self.port = data["port"]
            self.pid = data.get("pid")
        else:
            if self.port == 0:
                raise ValueError("Port must be supplied for new peer")
            self._persist()

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"id": self.id, "port": self.port}
        if self.pid:
            payload["pid"] = self.pid
        self.path.write_text(json.dumps(payload, indent=2))

    def start(self, memory_mb: int = 64) -> str:
        """
        Launch memcached, register the peer once confirmed alive.
        """
        proc = subprocess.Popen(
            ["memcached", "-d", "-m", str(memory_mb), "-p", str(self.port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        deadline = time.time() + 5
        self.pid = proc.pid
        client = self._client()

        while time.time() < deadline:
            try:
                client.stats()
                self._persist()
                _reg_add(self.id)
                return f"Peer {self.id} running on :{self.port}"
            except Exception:
                time.sleep(0.1)

        proc.terminate()
        raise RuntimeError(f"Failed to start peer {self.id} on :{self.port}")

    def stop(self) -> str:
        """
        Terminate the daemon and unregister the peer.
        """
        _get_client.cache_clear()
        return f"Peer {self.id} stopped."

    # ------------------------------------------------------------------ #
    # Cache operations
    # ------------------------------------------------------------------ #
    def _client(self) -> Client:
        """
        Return a *thread-local* cached Client so we don’t open thousands of
        sockets.  One (thread, port) → one TCP connection.
        """
        return _get_client(threading.get_ident(), self.port)

    def set(self, key: str, value: str) -> None:
        self._client().set(key, value)

    def get(self, key: str) -> Optional[bytes]:
        return self._client().get(key)

    def stats(self) -> Dict[str, Any]:
        raw = self._client().stats()
        return {
            (k.decode() if isinstance(k, bytes) else k): (
                v.decode() if isinstance(v, bytes) else v
            )
            for k, v in raw.items()
        }


@lru_cache(maxsize=None)
def _get_client(thread_id: int, port: int) -> Client:
    """Return a single pymemcache.Client per (thread, port) tuple."""
    return Client(
        ("localhost", port),
        connect_timeout=0.2,
        timeout=1.0,
        no_delay=True,
    )