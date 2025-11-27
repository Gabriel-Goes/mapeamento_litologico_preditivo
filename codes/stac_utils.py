from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from pystac_client import Client
import planetary_computer

from config import PC_STAC_URL, load_stac_catalog_config


def get_pc_client() -> Client:
    return Client.open(
        PC_STAC_URL,
        modifier=planetary_computer.sign_inplace,
    )


def open_stac_client(url: str) -> Client:
    """Abre um cliente STAC com assinatura automática quando necessário."""

    modifier = None
    if "planetarycomputer" in url:
        modifier = planetary_computer.sign_inplace

    return Client.open(url, modifier=modifier)


def iter_catalog_clients(
    sensor_key: str, catalogs: Optional[Dict[str, List[Dict[str, Any]]]] = None
) -> Iterator[Tuple[Dict[str, Any], Client]]:
    """Itera sobre catálogos STAC priorizados e devolve clientes prontos.

    Args:
        sensor_key: chave do sensor (ex.: ``"aster"`` ou ``"sentinel2"``).
        catalogs: configuração opcional; se omitida, usa ``load_stac_catalog_config``.

    Yields:
        Tuplas ``(catalog_config, client)`` seguindo a ordem de prioridade.
    """

    catalogs = catalogs or load_stac_catalog_config()
    catalog_list = catalogs.get(sensor_key, [])
    sorted_catalogs = sorted(catalog_list, key=lambda c: c.get("priority", 0))

    for catalog in sorted_catalogs:
        url = catalog.get("url")
        if not url:
            continue
        try:
            client = open_stac_client(url)
        except Exception as exc:
            print(f"[STAC] Falha ao abrir catálogo {url}: {exc}")
            continue

        yield catalog, client


def item_has_assets(item: Any, required: Iterable[str]) -> bool:
    assets = getattr(item, "assets", {}) or {}
    available = {k.upper() for k in assets.keys()}
    return all(req.upper() in available for req in required)


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
