#/codes/stac_clip_preview.py
"""STAC preview and clipping utilities for ASTER AST_07XT and Sentinel-2.

This module loads folha geometries from the database, queries STAC catalogs
for AST_07XT (e.g., NASA LPCLOUD) and Sentinel-2 L2A scenes, orders
candidates by cloud cover, and builds previews clipped to the folha extent.

Example CLI usage:
    python codes/stac_clip_preview.py --folha SB21_ZA_II2_NW \
        --aster-start 2000-01-01 --aster-end 2025-12-31

The CLI prints the best preview candidates and can optionally download the
accepted scenes (VNIR + SWIR for ASTER; RGB + NIR for Sentinel-2) clipped to
the folha polygon.
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

import rioxarray  # noqa: F401  # rioxarray activates .rio accessor
import stackstac
import xarray as xr
from pystac import Item
from pystac_client import Client
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from config import ORBITAL_DIR
from db_conn import get_folha_geom_geojson


ASTER_DEFAULT_URL = os.getenv("ASTER_STAC_URL", "https://cmr.earthdata.nasa.gov/stac/LPCLOUD")
ASTER_DEFAULT_COLLECTION = os.getenv("ASTER_STAC_COLLECTION", "AST_07XT_003")
S2_DEFAULT_URL = os.getenv("S2_STAC_URL", "https://planetarycomputer.microsoft.com/api/stac/v1")
S2_DEFAULT_COLLECTION = os.getenv("S2_STAC_COLLECTION", "sentinel-2-l2a")
DEFAULT_MAX_CLOUD = float(os.getenv("STAC_MAX_CLOUD", "30"))


@dataclass
class StacClipConfig:
    """Configuration hooks for STAC searches and downloads."""

    aster_url: str = ASTER_DEFAULT_URL
    aster_collection: str = ASTER_DEFAULT_COLLECTION
    sentinel_url: str = S2_DEFAULT_URL
    sentinel_collection: str = S2_DEFAULT_COLLECTION
    aster_dates: Tuple[str, str] = ("2000-01-01", "2025-12-31")
    sentinel_dates: Tuple[str, str] = ("2015-06-23", "2025-12-31")
    max_cloud: float = DEFAULT_MAX_CLOUD
    output_dir: Path = field(default_factory=lambda: Path(ORBITAL_DIR))


class CandidateIterator:
    """Iterate through candidates ordered by cloud cover ascending."""

    def __init__(
        self, items: Sequence[Item], preview_loader, folha_geom: BaseGeometry, sensor: str
    ) -> None:
        self.items = sorted(items, key=_cloud_score)
        self.preview_loader = preview_loader
        self.geom = folha_geom
        self.sensor = sensor
        self._index = 0

    def __iter__(self) -> Iterator[Tuple[Item, xr.DataArray]]:
        return self

    def __next__(self) -> Tuple[Item, xr.DataArray]:
        if self._index >= len(self.items):
            raise StopIteration
        item = self.items[self._index]
        self._index += 1
        preview = self.preview_loader(item, self.geom, self.sensor)
        return item, preview


def _cloud_score(item: Item) -> float:
    props: Dict[str, float] = item.properties or {}
    val = props.get("eo:cloud_cover") or props.get("s2:cloud_cover")
    if val is None:
        return 9999.0
    try:
        return float(val)
    except Exception:
        return 9999.0


class StacClipPreviewer:
    """High-level helper to search, preview, and clip ASTER and Sentinel-2 scenes."""

    def __init__(self, config: Optional[StacClipConfig] = None) -> None:
        self.config = config or StacClipConfig()
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, List[Item]] = {}

    def _folha_geometry(self, folha: str, conn_str: Optional[str] = None) -> BaseGeometry:
        geom_json = get_folha_geom_geojson(folha, conn_str=conn_str)
        return shape(geom_json)

    def _client(self, sensor: str) -> Client:
        if sensor == "aster":
            return Client.open(self.config.aster_url)
        if sensor == "sentinel":
            return Client.open(self.config.sentinel_url)
        raise ValueError(f"Unknown sensor {sensor}")

    def _collection(self, sensor: str) -> str:
        if sensor == "aster":
            return self.config.aster_collection
        if sensor == "sentinel":
            return self.config.sentinel_collection
        raise ValueError(f"Unknown sensor {sensor}")

    def _cache_key(
        self, sensor: str, folha: str, start_date: str, end_date: str
    ) -> str:
        return f"{sensor}:{folha}:{start_date}:{end_date}"

    def _supports_cloud_sort(
        self, client: Client, collection: str, intersects: Dict[str, object]
    ) -> bool:
        try:
            probe = client.search(
                collections=[collection], intersects=intersects, max_items=1
            )
            first = next(probe.items(), None)
        except Exception:
            return False
        if first is None:
            return False
        props = first.properties or {}
        return "eo:cloud_cover" in props

    def search_candidates(
        self,
        folha: str,
        sensor: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_cloud: Optional[float] = None,
        conn_str: Optional[str] = None,
    ) -> List[Item]:
        """Search candidates using pystac-client and cache the ordered list."""

        geom = self._folha_geometry(folha, conn_str=conn_str)
        geom_json = geom.__geo_interface__
        collection = self._collection(sensor)
        client = self._client(sensor)

        s_date = start_date or (
            self.config.aster_dates[0] if sensor == "aster" else self.config.sentinel_dates[0]
        )
        e_date = end_date or (
            self.config.aster_dates[1] if sensor == "aster" else self.config.sentinel_dates[1]
        )
        cloud_limit = max_cloud if max_cloud is not None else self.config.max_cloud

        cache_key = self._cache_key(sensor, folha, s_date, e_date)
        if cache_key in self._cache:
            return self._cache[cache_key]

        sortby = None
        if sensor == "aster":
            if self._supports_cloud_sort(client, collection, intersects=geom_json):
                sortby = ["+eo:cloud_cover"]
        else:
            sortby = ["+eo:cloud_cover"]

        search = client.search(
            collections=[collection],
            intersects=geom_json,
            datetime=f"{s_date}/{e_date}",
            max_items=200,
            sortby=sortby,
        )
        items = list(search.items())
        filtered = [i for i in items if _cloud_score(i) <= cloud_limit]
        ordered = sorted(filtered, key=_cloud_score)
        self._cache[cache_key] = ordered
        return ordered

    def iter_previews(
        self,
        folha: str,
        sensor: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_cloud: Optional[float] = None,
        conn_str: Optional[str] = None,
    ) -> CandidateIterator:
        items = self.search_candidates(
            folha,
            sensor,
            start_date=start_date,
            end_date=end_date,
            max_cloud=max_cloud,
            conn_str=conn_str,
        )
        geom = self._folha_geometry(folha, conn_str=conn_str)
        return CandidateIterator(items, self.load_preview, geom, sensor)

    def load_preview(self, item: Item, geom: BaseGeometry, sensor: str) -> xr.DataArray:
        asset = "B01" if sensor == "aster" else "B04"
        data = stackstac.stack([item], assets=[asset], epsg=4326).squeeze("time", drop=True)
        clipped = data.rio.clip([geom.__geo_interface__], crs="EPSG:4326", drop=True)
        return clipped

    def download_item(
        self,
        item: Item,
        geom: BaseGeometry,
        sensor: str,
        output_dir: Optional[Path] = None,
    ) -> xr.Dataset:
        """Download requested bands, clip to the folha polygon, and persist locally."""

        if sensor == "aster":
            assets = ["B01", "B02", "B3N", "B3B", "B04", "B05", "B06", "B07", "B08", "B09"]
        else:
            assets = ["B08", "B04", "B03", "B02"]

        ds = stackstac.stack([item], assets=assets, epsg=4326)
        ds = ds.rio.clip([geom.__geo_interface__], crs="EPSG:4326", drop=True)
        ds = ds.assign_coords(band=assets)

        out_dir = output_dir or self.config.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{item.collection_id}_{item.id}_clip.nc"
        ds.to_netcdf(out_path)
        return ds


def _parse_date(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None
    return date.fromisoformat(date_str).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview and clip STAC scenes for a folha.")
    parser.add_argument("--folha", required=True, help="Código da folha cartográfica (ex.: SB21_ZA_II2_NW)")
    parser.add_argument("--aster-start", dest="aster_start", default=None, help="Data inicial ASTER (YYYY-MM-DD)")
    parser.add_argument("--aster-end", dest="aster_end", default=None, help="Data final ASTER (YYYY-MM-DD)")
    parser.add_argument("--s2-start", dest="s2_start", default=None, help="Data inicial Sentinel-2 (YYYY-MM-DD)")
    parser.add_argument("--s2-end", dest="s2_end", default=None, help="Data final Sentinel-2 (YYYY-MM-DD)")
    parser.add_argument("--max-cloud", dest="max_cloud", type=float, default=DEFAULT_MAX_CLOUD)
    parser.add_argument("--accept", action="store_true", help="Aceita e baixa o melhor candidato de cada sensor")
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=ORBITAL_DIR,
        help="Diretório de saída para NetCDFs recortados",
    )
    args = parser.parse_args()

    cfg = StacClipConfig(
        aster_dates=(
            _parse_date(args.aster_start) or StacClipConfig().aster_dates[0],
            _parse_date(args.aster_end) or StacClipConfig().aster_dates[1],
        ),
        sentinel_dates=(
            _parse_date(args.s2_start) or StacClipConfig().sentinel_dates[0],
            _parse_date(args.s2_end) or StacClipConfig().sentinel_dates[1],
        ),
        max_cloud=args.max_cloud,
        output_dir=Path(args.output_dir),
    )
    previewer = StacClipPreviewer(cfg)

    for sensor in ("aster", "sentinel"):
        start, end = (cfg.aster_dates if sensor == "aster" else cfg.sentinel_dates)
        iterator = previewer.iter_previews(
            folha=args.folha,
            sensor=sensor,
            start_date=start,
            end_date=end,
            max_cloud=args.max_cloud,
        )
        try:
            item, preview = next(iterator)
        except StopIteration:
            print(f"Nenhum candidato encontrado para {sensor} no intervalo informado.")
            continue

        print(f"Melhor candidato {sensor}: {item.id} (cloud={_cloud_score(item):.2f})")
        print(f"Preview dims: {preview.shape}, CRS: {preview.rio.crs}")

        if args.accept:
            geom = previewer._folha_geometry(args.folha)
            ds = previewer.download_item(item, geom, sensor)
            print(f"Cena salva em {previewer.config.output_dir} com bandas {list(ds.band.values)}")


if __name__ == "__main__":
    main()
