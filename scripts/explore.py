"""
Inspect all raw shapefiles before any transformation.

Prints, for each layer type (census_summary, range_extent, extra_limit):
  - CRS per year (flags any mismatch)
  - Geometry type and row count
  - Column names (flags columns that appear/disappear across years)
  - Dtypes
  - One sample row

Run this before writing preprocess.py — USGS column names shift across years.

Usage:
    uv run python scripts/inspect.py
    uv run python scripts/inspect.py --layer census_summary   # filter one layer
    uv run python scripts/inspect.py --year 1985              # filter one year
"""

import argparse
import re
from pathlib import Path

import geopandas as gpd

RAW_DIR = Path("data/raw")

# Map filename fragments → canonical layer name
LAYER_PATTERNS = {
    "census_summary": re.compile(r"census.sum|Census.sum", re.IGNORECASE),
    "range_extent":   re.compile(r"range.extent|Range.extent|Range.Extent", re.IGNORECASE),
    "extra_limit":    re.compile(r"extra.limit|Extra.limit", re.IGNORECASE),
}


def classify_shp(path: Path) -> str | None:
    """Return canonical layer name for a shapefile, or None if unrecognised."""
    for layer, pat in LAYER_PATTERNS.items():
        if pat.search(path.stem):
            return layer
    return None


def extract_year(path: Path) -> int | None:
    """Best-effort year extraction from path components."""
    # 2015-2017: path contains the year as a directory name
    for part in path.parts:
        if re.fullmatch(r"20\d\d", part):
            return int(part)
    # 1985-2014: path contains SpringYYYY
    m = re.search(r"Spring(\d{4})", str(path))
    if m:
        return int(m.group(1))
    return None


def discover() -> dict[str, list[tuple[int, Path]]]:
    """
    Walk data/raw/ and return {layer_name: [(year, path), ...]} sorted by year.
    """
    layers: dict[str, list[tuple[int, Path]]] = {k: [] for k in LAYER_PATTERNS}
    for shp in sorted(RAW_DIR.rglob("*.shp")):
        layer = classify_shp(shp)
        year = extract_year(shp)
        if layer and year:
            layers[layer].append((year, shp))
    for k in layers:
        layers[k].sort()
    return layers


def print_layer_report(layer: str, entries: list[tuple[int, Path]]) -> None:
    bar = "=" * 70
    print(f"\n{bar}")
    print(f"  LAYER: {layer}  ({len(entries)} years)")
    print(bar)

    all_cols: dict[int, list[str]] = {}
    all_crs: dict[int, str] = {}

    for year, path in entries:
        gdf = gpd.read_file(path)
        crs_str = gdf.crs.to_string() if gdf.crs else "None"
        all_cols[year] = list(gdf.columns)
        all_crs[year] = crs_str

        print(f"\n  --- {year} ---")
        print(f"  path     : {path.relative_to(RAW_DIR)}")
        print(f"  CRS      : {crs_str}")
        # EPSG code is the fast lookup for reprojection — flag if missing
        epsg = gdf.crs.to_epsg() if gdf.crs else None
        print(f"  EPSG     : {epsg if epsg else '(no EPSG code — check CRS manually)'}")
        print(f"  geom type: {gdf.geom_type.unique().tolist()}")
        print(f"  rows     : {len(gdf)}")
        print(f"  columns  : {list(gdf.columns)}")
        print(f"  dtypes   :")
        for col, dtype in gdf.dtypes.items():
            print(f"             {col:<30} {dtype}")
        if len(gdf):
            print(f"  sample   :")
            row = gdf.iloc[0].drop("geometry")
            for col, val in row.items():
                print(f"             {col:<30} {val!r}")

    # Cross-year column consistency check
    if len(entries) > 1:
        col_sets = {y: set(c) - {"geometry"} for y, c in all_cols.items()}
        all_union = set().union(*col_sets.values())
        all_inter = set.intersection(*col_sets.values())
        cols_only_some = all_union - all_inter

        print(f"\n  --- column consistency across {len(entries)} years ---")
        if not cols_only_some:
            print("  All years share identical non-geometry columns.")
        else:
            print("  Columns present in SOME but not ALL years:")
            for col in sorted(cols_only_some):
                present_in = sorted(y for y, s in col_sets.items() if col in s)
                print(f"    {col:<30} years: {present_in}")

        # CRS consistency check
        unique_crs = set(all_crs.values())
        if len(unique_crs) == 1:
            print(f"  CRS is consistent across all years.")
        else:
            print("  CRS VARIES across years — must normalise in preprocess.py:")
            for crs_val in sorted(unique_crs):
                years = [y for y, c in all_crs.items() if c == crs_val]
                print(f"    {crs_val}")
                print(f"      years: {years}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect raw sea otter shapefiles")
    parser.add_argument("--layer", choices=list(LAYER_PATTERNS), help="Inspect one layer only")
    parser.add_argument("--year", type=int, help="Inspect one year only")
    args = parser.parse_args()

    layers = discover()

    total = sum(len(v) for v in layers.values())
    print(f"Found {total} shapefiles across {len(layers)} layer types")
    for k, v in layers.items():
        years = [y for y, _ in v]
        print(f"  {k:<20} {len(v)} years  {min(years) if years else '?'}–{max(years) if years else '?'}")

    for layer, entries in layers.items():
        if args.layer and layer != args.layer:
            continue
        if args.year:
            entries = [(y, p) for y, p in entries if y == args.year]
            if not entries:
                continue
        print_layer_report(layer, entries)


if __name__ == "__main__":
    main()
