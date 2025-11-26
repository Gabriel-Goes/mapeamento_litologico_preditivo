from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pystac_client import Client
import planetary_computer

from config import PC_STAC_URL


def get_pc_client() -> Client:
    return Client.open(
        PC_STAC_URL,
        modifier=planetary_computer.sign_inplace,
    )


def item_datetime(item: Any) -> datetime:
    if getattr(item, "datetime", None) is not None:
        dt = item.datetime
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    props: Dict[str, Any] = getattr(item, "properties", {}) or {}
    dt_str = props.get("datetime") or props.get("start_datetime")
    if dt_str is None:
        raise RuntimeError(f"Item {getattr(item, 'id', '?')} sem campo datetime.")

    if dt_str.endswith("Z"):
        dt_str = dt_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def get_cloud_cover(item: Any) -> Optional[float]:
    props: Dict[str, Any] = getattr(item, "properties", {}) or {}
    for key in ("eo:cloud_cover", "s2:cloud_cover"):
        value = props.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except Exception:
            continue
    return None


def get_signed_item(collection_id: str, item_id: str) -> Any:
    api = get_pc_client()
    search = api.search(
        collections=[collection_id],
        ids=[item_id],
        max_items=1,
    )
    item = next(search.items(), None)
    if item is None:
        raise RuntimeError(f"Item {item_id} não encontrado na coleção {collection_id}")
    return item
