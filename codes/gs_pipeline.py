from __future__ import annotations

import argparse
from typing import List

from gs_fusion import run_gs_pair_pipeline
from config import ORBITAL_DIR


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folha", required=True)
    parser.add_argument("--aster-collection", default="aster-l1t")
    parser.add_argument("--aster-id", required=True)
    parser.add_argument("--s2-collection", default="sentinel-2-l2a")
    parser.add_argument("--s2-id", required=True)
    parser.add_argument(
        "--s2-bands",
        nargs="+",
        default=[
            "B02", "B03", "B04",
            "B05", "B06", "B07", "B08", "B8A",
            "B11", "B12",
        ],
    )
    parser.add_argument("--out-dir", default=ORBITAL_DIR)
    args = parser.parse_args()

    print("=" * 80)
    print(f"[GS PIPELINE] Folha: {args.folha}")
    print("=" * 80)

    s2_band_ids: List[str] = list(args.s2_bands)
    run_gs_pair_pipeline(
        folha_codigo=args.folha,
        aster_collection=args.aster_collection,
        aster_id=args.aster_id,
        s2_collection=args.s2_collection,
        s2_id=args.s2_id,
        s2_band_ids=s2_band_ids,
        out_dir=args.out_dir,
    )


if __name__ == "__main__":
    main()
