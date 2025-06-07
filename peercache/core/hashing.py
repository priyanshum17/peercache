import hashlib
import bisect
from typing import List, Dict


def _h32(data: str) -> int:
    """Return a 32-bit *stable* hash for the given string."""
    return int(hashlib.md5(data.encode()).hexdigest()[:8], 16)


class ConsistentHashRing:
    """
    Consistent-hash ring with V virtual nodes per peer.
    """

    def __init__(self, peer_ids: List[str], virtual_nodes: int = 100) -> None:
        self.vnodes: Dict[int, str] = {}
        self.ring: List[int] = []

        for pid in set(peer_ids):
            for v in range(virtual_nodes):
                h = _h32(f"{pid}#{v}")
                self.vnodes[h] = pid
                self.ring.append(h)

        self.ring.sort()

    def get_n(self, key: str, n: int = 1) -> List[str]:
        """
        Return up to *n* distinct peer_ids responsible for *key*.

        If the requested replication factor exceeds the number of peers on the
        ring, the list is truncated to the available peers.
        """
        if not self.ring:
            return list()

        # Prevent infinite loop if n > unique peers
        max_distinct = len(set(self.vnodes.values()))
        n = max(1, min(n, max_distinct))

        h = _h32(key)
        idx = bisect.bisect(self.ring, h)

        result: List[str] = []
        while len(result) < n:
            pid = self.vnodes[self.ring[idx % len(self.ring)]]
            if pid not in result:
                result.append(pid)
            idx += 1

        return result
