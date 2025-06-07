import hashlib
import bisect
from typing import List


def _h32(data: str) -> int:
    """32-bit stable hash."""
    return int(hashlib.md5(data.encode()).hexdigest()[:8], 16)


class ConsistentHashRing:
    """
    Consistent hashing with V virtual nodes per peer.
    """

    def __init__(self, peer_ids: List[str], virtual_nodes: int = 100):
        self.vnodes = {}
        self.ring = []  # sorted list of hashes
        for pid in peer_ids:
            for v in range(virtual_nodes):
                h = _h32(f"{pid}#{v}")
                self.vnodes[h] = pid
                self.ring.append(h)
        self.ring.sort()

    def get_n(self, key: str, n: int = 1) -> List[str]:
        """
        Return N distinct peer_ids responsible for 'key'.
        Used for replication factor R.
        """
        if not self.ring:
            return []
        h = _h32(key)
        idx = bisect.bisect(self.ring, h)
        result = []
        while len(result) < n:
            pid = self.vnodes[self.ring[idx % len(self.ring)]]
            if pid not in result:
                result.append(pid)
            idx += 1
        return result
