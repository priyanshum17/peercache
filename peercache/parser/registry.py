import json
from pathlib import Path
from peercache.settings.settings import SETTINGS

_REG_PATH = Path(SETTINGS.PEER_FOLDER_PATH) / "registry.json"


def _load() -> set[str]:
    if _REG_PATH.exists():
        return set(json.loads(_REG_PATH.read_text()))
    return set()


def _save(peers: set[str]):
    _REG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REG_PATH.write_text(json.dumps(sorted(peers), indent=2))


def add(peer_id: str):
    peers = _load()
    peers.add(peer_id)
    _save(peers)


def remove(peer_id: str):
    peers = _load()
    peers.discard(peer_id)
    _save(peers)


def list_peers() -> list[str]:
    return sorted(_load())
