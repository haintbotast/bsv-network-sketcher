"""
Layout Cache - In-memory cache for auto-layout results.

Caches layout results based on topology hash to avoid recomputing
when topology hasn't changed.
"""

import hashlib
import json
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class CachedLayout:
    """Cached layout result with topology hash."""
    topology_hash: str
    result: dict  # LayoutResult as dict
    timestamp: float  # Unix timestamp


class LayoutCache:
    """In-memory cache for layout results."""

    def __init__(self):
        self._cache: dict[str, CachedLayout] = {}

    def compute_topology_hash(self, devices: list, links: list) -> str:
        """
        Compute SHA256 hash of topology.

        Hash is based on:
        - Device IDs (sorted)
        - Link connections (from_device_id, to_device_id, purpose) sorted

        Args:
            devices: List of Device model instances
            links: List of L1Link model instances

        Returns:
            SHA256 hash string
        """
        # Extract device IDs
        device_ids = sorted([d.id for d in devices])

        # Extract link tuples
        link_tuples = sorted([
            (l.from_device_id, l.to_device_id, l.purpose)
            for l in links
        ])

        # Create hash input
        hash_input = {
            "devices": device_ids,
            "links": link_tuples,
        }

        hash_str = json.dumps(hash_input, sort_keys=True)
        return hashlib.sha256(hash_str.encode()).hexdigest()

    def get(self, project_id: str, topology_hash: str) -> Optional[dict]:
        """
        Get cached layout result.

        Args:
            project_id: Project ID
            topology_hash: Topology hash

        Returns:
            Cached result dict or None if not found/invalid
        """
        cache_key = f"{project_id}:{topology_hash}"

        if cache_key not in self._cache:
            return None

        cached = self._cache[cache_key]

        # Verify hash matches
        if cached.topology_hash != topology_hash:
            return None

        return cached.result

    def set(self, project_id: str, topology_hash: str, result: dict) -> None:
        """
        Cache layout result.

        Args:
            project_id: Project ID
            topology_hash: Topology hash
            result: LayoutResult as dict
        """
        import time

        cache_key = f"{project_id}:{topology_hash}"

        self._cache[cache_key] = CachedLayout(
            topology_hash=topology_hash,
            result=result,
            timestamp=time.time(),
        )

    def invalidate(self, project_id: str) -> None:
        """
        Invalidate all cached layouts for a project.

        Args:
            project_id: Project ID
        """
        keys_to_delete = [k for k in self._cache if k.startswith(f"{project_id}:")]
        for key in keys_to_delete:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cached layouts."""
        self._cache.clear()


# Global cache instance
_cache_instance: Optional[LayoutCache] = None


def get_cache() -> LayoutCache:
    """Get global cache instance (singleton)."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LayoutCache()
    return _cache_instance
