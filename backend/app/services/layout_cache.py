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

    def compute_topology_hash(self, devices: list, links: list, options: dict | None = None, extra_data: list | None = None) -> str:
        """
        Compute SHA256 hash of topology.

        Hash is based on:
        - Device IDs (sorted)
        - Link connections (from_device_id, to_device_id, purpose) sorted
        - Options (layout parameters)
        - Extra data (areas, l2_assignments, l3_addresses) - optional

        Args:
            devices: List of Device model instances
            links: List of L1Link model instances
            options: Layout options dict (optional)
            extra_data: List of Area/L2Assignment/L3Address instances (optional)

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
        if options:
            hash_input["options"] = options
        if extra_data:
            # Handle different types of extra data
            extra_tuples = []
            for item in extra_data:
                # Check type by attributes
                if hasattr(item, 'grid_row') and hasattr(item, 'grid_col'):
                    # Area model
                    extra_tuples.append((
                        'area',
                        item.id,
                        item.position_x,
                        item.position_y,
                        item.width,
                        item.height,
                        item.grid_row,
                        item.grid_col,
                    ))
                elif hasattr(item, 'l2_segment_id'):
                    # InterfaceL2Assignment model
                    extra_tuples.append((
                        'l2_assignment',
                        item.id,
                        item.device_id,
                        item.interface_name,
                        item.l2_segment_id,
                    ))
                elif hasattr(item, 'ip_address') and hasattr(item, 'prefix_length'):
                    # L3Address model
                    extra_tuples.append((
                        'l3_address',
                        item.id,
                        item.device_id,
                        item.interface_name,
                        item.ip_address,
                        item.prefix_length,
                    ))
                else:
                    # Generic fallback: just use ID
                    extra_tuples.append(('unknown', getattr(item, 'id', str(item))))

            hash_input["extra_data"] = sorted(extra_tuples)

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
