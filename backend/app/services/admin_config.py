"""Admin config service."""

import json
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdminConfig


DEFAULT_ADMIN_CONFIG: Dict[str, Any] = {
    "layout_tuning": {
        "layer_gap": 1.5,
        "node_spacing": 0.8,
        "port_label_band": 0.2,
        "area_gap": 1.1,
        "area_padding": 0.35,
        "label_band": 0.5,
        "max_row_width_base": 12.0,
        "max_nodes_per_row": 8,
        "row_gap": 0.5,
        "row_stagger": 0.5,
    },
    "render_tuning": {
        "port_edge_inset": 6,
        "port_label_offset": 12,
        "bundle_gap": 18,
        "bundle_stub": 18,
        "area_clearance": 18,
        "area_anchor_offset": 18,
        "label_gap_x": 8,
        "label_gap_y": 6,
        "corridor_gap": 40,
    },
}


def _merge_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(DEFAULT_ADMIN_CONFIG)
    merged_layout = dict(DEFAULT_ADMIN_CONFIG.get("layout_tuning", {}))
    merged_render = dict(DEFAULT_ADMIN_CONFIG.get("render_tuning", {}))

    merged_layout.update(config.get("layout_tuning", {}) if isinstance(config.get("layout_tuning"), dict) else {})
    merged_render.update(config.get("render_tuning", {}) if isinstance(config.get("render_tuning"), dict) else {})

    merged["layout_tuning"] = merged_layout
    merged["render_tuning"] = merged_render
    return merged


async def get_admin_config(db: AsyncSession, config_key: str = "global") -> Dict[str, Any]:
    result = await db.execute(select(AdminConfig).where(AdminConfig.config_key == config_key))
    record = result.scalar_one_or_none()
    if not record:
        return DEFAULT_ADMIN_CONFIG
    try:
        payload = json.loads(record.config_json)
    except Exception:
        payload = {}
    return _merge_defaults(payload if isinstance(payload, dict) else {})


async def upsert_admin_config(
    db: AsyncSession,
    config: Dict[str, Any],
    config_key: str = "global",
) -> AdminConfig:
    result = await db.execute(select(AdminConfig).where(AdminConfig.config_key == config_key))
    record = result.scalar_one_or_none()
    payload = _merge_defaults(config if isinstance(config, dict) else {})
    if record:
        record.config_json = json.dumps(payload)
        record.updated_at = datetime.utcnow()
    else:
        record = AdminConfig(config_key=config_key, config_json=json.dumps(payload))
        db.add(record)
    await db.commit()
    await db.refresh(record)
    return record
