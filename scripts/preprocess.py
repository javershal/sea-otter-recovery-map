"""
Reproject, simplify, and merge all raw shapefiles into three GeoJSON files.

Outputs (all EPSG:4326, all years combined, one feature per segment per year):
    docs/data/census_summary.geojson
    docs/data/range_extent.geojson
    docs/data/extra_limit.geojson

Every feature has a `year` property (integer) so the MapLibre frontend can
filter with ["==", ["get", "year"], 1985].

Idempotent: running twice produces identical output.

Usage:
    uv run python scripts/preprocess.py
    uv run python scripts/preprocess.py --layer census_summary  # one layer only
"""

import argparse
import json
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd

RAW_DIR = Path("data/raw")
OUT_DIR = Path("docs/data")

# Simplification tolerance in EPSG:3310 metres.
# At zoom 10 (~150 m/pixel on screen) this keeps geometry smooth without bloat.
SIMPLIFY_M = 50

LAYER_PATTERNS = {
    "census_summary": re.compile(r"census.sum", re.IGNORECASE),
    "range_extent":   re.compile(r"range.extent", re.IGNORECASE),
    "extra_limit":    re.compile(r"extra.limit", re.IGNORECASE),
}

# Columns to carry through to the frontend per layer (geometry + year added separately)
KEEP_COLS = {
    "census_summary": ["lin_dens"],
    "range_extent":   [],          # geometry-only; the line shape is the whole story
    "extra_limit":    ["Count"],
}


# ---------------------------------------------------------------------------
# Discovery helpers (same logic as explore.py)
# ---------------------------------------------------------------------------

def classify_shp(path: Path) -> str | None:
    for layer, pat in LAYER_PATTERNS.items():
        if pat.search(path.stem):
            return layer
    return None


def extract_year(path: Path) -> int | None:
    for part in path.parts:
        if re.fullmatch(r"20\d\d", part):
            return int(part)
    m = re.search(r"Spring(\d{4})", str(path))
    return int(m.group(1)) if m else None


def discover(layer_filter: str | None) -> dict[str, list[tuple[int, Path]]]:
    layers: dict[str, list[tuple[int, Path]]] = {k: [] for k in LAYER_PATTERNS}
    for shp in sorted(RAW_DIR.rglob("*.shp")):
        layer = classify_shp(shp)
        year = extract_year(shp)
        if layer and year:
            layers[layer].append((year, shp))
    for k in layers:
        layers[k].sort()
    if layer_filter:
        return {layer_filter: layers[layer_filter]}
    return layers


# ---------------------------------------------------------------------------
# Per-year processing
# ---------------------------------------------------------------------------

def process_year(path: Path, year: int, layer: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)

    # Confirm source CRS is EPSG:3310 (California Albers, NAD83).
    # All USGS sea otter shapefiles use this projection.
    assert gdf.crs and gdf.crs.to_epsg() == 3310, (
        f"Unexpected CRS {gdf.crs} in {path} — check projection before proceeding"
    )

    # Simplify in the source CRS (metres) before reprojecting.
    # Doing it here avoids distortion from simplifying in degrees.
    if layer != "extra_limit":  # points can't be simplified
        gdf["geometry"] = gdf.geometry.simplify(SIMPLIFY_M, preserve_topology=True)

    # Reproject EPSG:3310 → EPSG:4326 (WGS84 lat/lon).
    # MapLibre GL JS expects 4326; it handles Web Mercator internally.
    gdf = gdf.to_crs(4326)

    # Normalise year: sources vary between int32, float64, or absent (range_extent)
    gdf["year"] = year  # always use the year we extracted from the filename

    # Drop everything except the columns we need + geometry
    keep = KEEP_COLS[layer] + ["year", "geometry"]
    # Only keep columns that actually exist (defensive against schema drift)
    keep = [c for c in keep if c in gdf.columns]
    gdf = gdf[keep]

    # Cast Count to int for extra_limit (stored as float in source)
    if "Count" in gdf.columns:
        gdf["Count"] = gdf["Count"].fillna(0).astype(int)

    return gdf


# ---------------------------------------------------------------------------
# Layer merge and write
# ---------------------------------------------------------------------------

def process_layer(layer: str, entries: list[tuple[int, Path]]) -> None:
    print(f"\n  [{layer}] {len(entries)} years", end="", flush=True)

    frames = []
    for year, path in entries:
        frames.append(process_year(path, year, layer))
        print(".", end="", flush=True)

    merged = pd.concat(frames, ignore_index=True)
    merged = gpd.GeoDataFrame(merged, crs=4326)

    out_path = OUT_DIR / f"{layer}.geojson"
    # Write atomically: .tmp → final so a half-written file never exists
    tmp_path = out_path.with_suffix(".geojson.tmp")
    merged.to_file(tmp_path, driver="GeoJSON")
    tmp_path.rename(out_path)

    size_kb = out_path.stat().st_size // 1024
    print(f" → {out_path}  ({len(merged):,} features, {size_kb:,} KB)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess raw shapefiles into web GeoJSON")
    parser.add_argument("--layer", choices=list(LAYER_PATTERNS), help="Process one layer only")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    layers = discover(args.layer)

    total_years = sum(len(v) for v in layers.values())
    print(f"Processing {total_years} shapefiles across {len(layers)} layer(s)...")

    for layer, entries in layers.items():
        if not entries:
            print(f"\n  [{layer}] no shapefiles found — skipping")
            continue
        process_layer(layer, entries)

    print("\nDone.")


if __name__ == "__main__":
    main()
