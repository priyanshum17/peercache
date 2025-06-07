import json
from pathlib import Path
from typing import List

from peercache.settings.settings import SETTINGS
from peercache.parser.peer import Peer
from peercache.core.hashing import ConsistentHashRing


class Network:
    """
    A single Memcached network with a consistent-hash ring and optional replication.
    Each network is stored in state/network/<name>.json
    """

    def __init__(self, name: str, replication: int = 1, vnodes: int = 100) -> None:
        self.name = name
        self.peers: List[str] = []
        self.write = True
        self.replication = replication
        self.vnodes = vnodes
        self.file_path = Path(SETTINGS.NETWORKS_FOLDER_PATH) / f"{self.name}.json"

        self._load_or_initialize()
        self._build_ring()

    def _load_or_initialize(self):
        if self.file_path.exists():
            try:
                with open(self.file_path, "r") as f:
                    data = json.load(f)
                self.peers = data.get("peers", [])
                self.write = data.get("write", True)
                self.replication = data.get("replication", self.replication)
                self.vnodes = data.get("vnodes", self.vnodes)
            except (json.JSONDecodeError, IOError):
                self.peers = []
        else:
            self._save()

    def _save(self):
        payload = {
            "name": self.name,
            "peers": self.peers,
            "write": self.write,
            "replication": self.replication,
            "vnodes": self.vnodes,
        }
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(json.dumps(payload, indent=2))

    def _build_ring(self):
        self.ring = ConsistentHashRing(self.peers, virtual_nodes=self.vnodes)

    def add_peer(self, peer_id: str) -> str:
        if peer_id not in self.peers:
            self.peers.append(peer_id)
            self._save()
            self._build_ring()
            return f"Peer '{peer_id}' added to network '{self.name}'."
        return f"Peer '{peer_id}' already exists in network '{self.name}'."

    def remove_peer(self, peer_id: str) -> str:
        if peer_id in self.peers:
            self.peers.remove(peer_id)
            self._save()
            self._build_ring()
            return f"Peer '{peer_id}' removed from network '{self.name}'."
        return f"Peer '{peer_id}' not found in network '{self.name}'."

    def cache_set(self, key: str, value: str) -> str:
        if not self.peers:
            return "No peers available."
        targets = self.ring.get_n(key, self.replication)
        for pid in targets:
            Peer(pid).set(key, value)
        return f"SET {key} replicated to {targets}"

    def cache_get(self, key: str) -> str:
        if not self.peers:
            return "No peers available."
        for pid in self.ring.get_n(key, self.replication):
            val = Peer(pid).get(key)
            if val is not None:
                return val.decode()
        return "MISS"

    def stats(self) -> str:
        return (
            f"Network: {self.name}\n"
            f"Peers  : {', '.join(self.peers) if self.peers else 'None'}\n"
            f"Write  : {self.write}\n"
            f"Replicas: {self.replication} | VNodes: {self.vnodes}"
        )

    def __str__(self) -> str:
        return self.stats()
