"""
Populate data/raw/ with USGS California Sea Otter Census shapefiles.

1985-2014: extracted from locally-archived zips in '1985-2014 zips/'.
           (The ScienceBase item 5a32d390e4b08e6a89d88583 has unpublished files
           that 404 over HTTP; the zips were recovered from the Internet Archive.)
2015-2017: downloaded live from ScienceBase — these items are publicly accessible.
           2015 has no extra-limit observations layer (USGS did not publish one).
           2011 is absent from all sources — USGS did not conduct the census that year.

Usage:
    uv run python scripts/download.py                          # skip already-done work
    uv run python scripts/download.py --force                  # redo everything
    uv run python scripts/download.py --archive-dir /some/path # custom zip location
"""

import argparse
import zipfile
from pathlib import Path

import requests

RAW_DIR = Path("data/raw")
DEFAULT_ARCHIVE_DIR = Path("1985-2014 zips")
SB_BASE = "https://www.sciencebase.gov"

# 2015-2017: separate ScienceBase items per layer per year.
RECENT_ITEMS: dict[int, dict[str, str]] = {
    2015: {
        "census_summary": "55e60f3ce4b05561fa2087e9",
        "range_extent":   "55e61386e4b05561fa2087fa",
        # no extra_limit published for 2015
    },
    2016: {
        "census_summary": "57a34e7be4b006cb45567bd0",
        "range_extent":   "57a3513ee4b006cb45567d47",
        "extra_limit":    "57a3508ae4b006cb45567cec",
    },
    2017: {
        "census_summary": "59bc4169e4b091459a591363",
        "range_extent":   "59bc4251e4b091459a591370",
        "extra_limit":    "59bc41f2e4b091459a59136a",
    },
}


def item_zip_url(item_id: str) -> str:
    """ScienceBase endpoint that bundles all files for an item as one zip."""
    return f"{SB_BASE}/catalog/file/get/{item_id}"


def download_file(url: str, dest: Path, force: bool) -> bool:
    """
    Download url → dest using a .tmp swap so interrupted downloads never leave a
    corrupt file behind.  Returns True if a download actually happened.
    """
    if dest.exists() and not force:
        # HEAD request to compare size — cheap idempotency check
        head = requests.head(url, timeout=30, allow_redirects=True)
        expected = int(head.headers.get("content-length", 0)) or None
        if expected is None or dest.stat().st_size == expected:
            print(f"    skip  {dest.name}")
            return False
        print(f"    stale {dest.name} (size mismatch — re-downloading)")

    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.unlink(missing_ok=True)

    print(f"    fetch {dest.name} ...", end="", flush=True)
    resp = requests.get(url, stream=True, timeout=300)
    if resp.status_code != 200:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"HTTP {resp.status_code} fetching {url}")

    with tmp.open("wb") as fh:
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            fh.write(chunk)

    tmp.rename(dest)
    print(f" {dest.stat().st_size // 1024:,} KB")
    return True


def extract_zip(zip_path: Path, extract_to: Path, force: bool) -> None:
    """Extract zip_path into extract_to/, skipping if already done."""
    sentinel = extract_to / ".extracted"
    if sentinel.exists() and not force:
        print(f"    skip  extract {zip_path.name}")
        return

    extract_to.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        top = sorted({p.split("/")[0] for p in zf.namelist()})
        print(f"    unzip {zip_path.name} → {extract_to.name}/ ({len(zf.namelist())} files, top: {top})")
        zf.extractall(extract_to)

    sentinel.touch()


def extract_archive(archive_dir: Path, force: bool) -> None:
    """
    Extract the 1985-2014 per-year zips from the local archive directory into
    data/raw/1985_2014/{year}/.
    """
    print(f"\n=== 1985-2014 (from {archive_dir}) ===")
    if not archive_dir.exists():
        raise FileNotFoundError(
            f"Archive directory not found: {archive_dir}\n"
            "Download the 1985-2014 zips from the Internet Archive and place them there."
        )

    year_zips = sorted(archive_dir.glob("Spring*.zip"))
    print(f"  found {len(year_zips)} per-year zips")

    for zip_path in year_zips:
        extract_to = RAW_DIR / "1985_2014" / zip_path.stem
        extract_zip(zip_path, extract_to, force)


def download_recent(force: bool) -> None:
    """Download shapefile layers for 2015-2017 from ScienceBase."""
    for year, layers in RECENT_ITEMS.items():
        print(f"\n=== {year} ({len(layers)} layers) ===")
        for layer, item_id in layers.items():
            dest_dir = RAW_DIR / str(year) / layer
            dest_dir.mkdir(parents=True, exist_ok=True)

            zip_path = dest_dir / f"{layer}_{year}.zip"
            download_file(item_zip_url(item_id), zip_path, force)
            extract_zip(zip_path, dest_dir, force)


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate data/raw/ with sea otter census shapefiles")
    parser.add_argument("--force", action="store_true", help="Re-extract/re-download all files")
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE_DIR,
                        help="Directory containing 1985-2014 Spring*.zip files")
    args = parser.parse_args()

    # Clean up any .tmp files from prior interrupted downloads
    for tmp in RAW_DIR.rglob("*.tmp"):
        print(f"cleaning up interrupted download: {tmp}")
        tmp.unlink()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    extract_archive(args.archive_dir, args.force)
    download_recent(args.force)
    print("\nAll done.")


if __name__ == "__main__":
    main()
