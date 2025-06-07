import json
import subprocess
import time
from pathlib import Path
import socket

from peercache.settings.settings import SETTINGS
from pymemcache.client.base import Client
from peercache.parser.registry import add as _reg_add, remove as _reg_rm


class Peer:
    def __init__(self, peer_id: str, port: int | None = None):
        self.id = peer_id
        self.port = port if port is not None else self._find_free_port()
        self.path = Path(SETTINGS.PEER_FOLDER_PATH) / f"{self.id}.json"
        self._load_or_init()

    def _find_free_port(self, min_port=20000, max_port=30000) -> int:
        """Find a free port within a safe custom range for Memcached peers."""
        for port in range(min_port, max_port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("localhost", port))
                    return port
                except OSError:
                    continue
        raise RuntimeError("No free port available in the safe range.")

    def _load_or_init(self):
        if self.path.exists():
            data = json.loads(self.path.read_text())
            self.port = data["port"]
        else:
            if self.port == 0:
                raise ValueError("Port must be supplied for new peer")
            self._save()

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"id": self.id, "port": self.port}, indent=2))
        _reg_add(self.id)

    def start(self, memory_mb: int = 64) -> str:
        subprocess.Popen(
            ["memcached", "-d", "-m", str(memory_mb), "-p", str(self.port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.2)
        return f"Peer {self.id} running on :{self.port}"

    def stop(self) -> str:
        subprocess.call(["pkill", "-f", f"memcached.*-p {self.port}"])
        _reg_rm(self.id)
        return f"Peer {self.id} stopped."

    def _client(self) -> Client:
        return Client(("localhost", self.port), connect_timeout=1, timeout=1)

    def set(self, k: str, v: str):
        self._client().set(k, v)

    def get(self, k: str):
        return self._client().get(k)

    def stats(self) -> dict:
        return self._client().stats()
