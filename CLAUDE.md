# CLAUDE.md

Project context and guardrails for Claude Code working on this repository.

## Project

**Sea Otter Recovery Map** — an interactive web map of the California coast with a year scrubber (1985–2017) that animates the density and range of southern sea otters (*Enhydra lutris nereis*) as they recover from near-extinction.

This is a learning project. The owner is using it to learn GIS hands-on. Optimize for clarity and explanation, not cleverness.

## What "done" looks like for v1

- Single-page static site (no backend, no build step required)
- MapLibre GL JS map centered on the central California coast
- Bottom year scrubber (1985–2017) with play/pause
- Three layers driven by the current year: density polygons (the heatmap), range extent polyline, extra-limit point observations
- Small panel showing the year's total count and range span
- Deployable to GitHub Pages or Cloudflare Pages with no configuration

That is the whole scope. Resist suggesting features beyond it until v1 ships.

## Data

Source: USGS Annual California Sea Otter Census, 1985–2014 archive (ScienceBase item `5a32d390e4b08e6a89d88583`) plus the individual 2015, 2016, 2017 releases.

Each year provides three shapefiles:

| Shapefile | Geometry | Meaning | Role in viz |
|---|---|---|---|
| Census summary | Polygons | Coast segments with otter density, linear density, pup ratio, 5-year trend | The heatmap layer |
| Range extent | Polyline | Official northern + southern limits of the population | Range indicator |
| Extra limit observations | Points | Individual otters (usually males) outside the official range | The pioneers — narratively important |

The 1985–2014 archive likely uses a California-specific projection (Albers / NAD83 Teale Albers). Inspect it; don't assume.

## Architecture

```
otter-recovery/
├── data/
│   ├── raw/              # downloaded shapefiles, gitignored
│   └── processed/        # output GeoJSON
├── scripts/
│   ├── download.py       # fetch USGS data
│   ├── explore.py        # exploratory — print CRS, columns, samples
│   └── preprocess.py     # reproject, simplify, merge by year property
├── docs/
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── data/             # the three merged GeoJSON files
├── CLAUDE.md
├── README.md
├── pyproject.toml
└── .gitignore
```

Two halves: Python pipeline → static frontend. They communicate only through files in `docs/data/`. Keep that boundary clean.

## Data model conventions

Preprocessing produces three GeoJSON files, each with all years combined:

- `docs/data/census_summary.geojson`
- `docs/data/range_extent.geojson`
- `docs/data/extra_limit.geojson`

Every feature has a `year` property (integer, e.g. `1985`). The frontend uses MapLibre filter expressions like `["==", ["get", "year"], 1985]` to swap visibility — no per-year files, no rebuilds.

All output is EPSG:4326 (WGS84 lat/lon). MapLibre handles the Web Mercator reprojection internally.

## Guardrails

- **No backend, no API server, no database.** This is a static site.
- **No frontend framework, no build step, no bundler** without asking first. Plain HTML + JS loaded from CDN is the target.
- **No new dependencies** beyond GeoPandas, Shapely, pyogrio, and requests/httpx without asking. The Python side should stay small.
- **Preprocessing must be idempotent.** Running `preprocess.py` twice produces identical output.
- **Don't commit the raw shapefiles.** They go in `data/raw/` which is gitignored. Re-downloadable from USGS.
- **Inspect before transforming.** When working with a new shapefile, print its CRS, columns, dtypes, and a sample row before writing transformation code. The USGS column names are not standardized across years — verify.
- **Stay in scope.** If a change feels like it needs new infrastructure (a tile server, a backend, a database), stop and ask before building it.

## Teaching mode

The owner is learning GIS. When you make a non-obvious GIS decision, add a one-line comment in the code explaining why. Specifically:

- Any CRS conversion: note the source EPSG, the target EPSG, and why
- Any geometry simplification: note the tolerance and what it means at the target zoom levels
- Any spatial operation (join, buffer, intersect): one sentence on what it does and why we need it
- Any MapLibre expression that isn't obvious: one comment on what attribute it's reading and what visual effect it produces

Don't over-comment trivial code. The goal is to flag the GIS-specific moments, not narrate every line.

When the owner asks "why did you do X," prefer a short, direct explanation over a generic tutorial. They will ask follow-ups if they want depth.

## Style

- Python: use `uv` for env management. Standard formatting (ruff defaults). Type hints where they help readability, not everywhere.
- JS: vanilla ES modules, no transpilation. Modern browser targets only.
- HTML/CSS: single `index.html`, single `style.css`. Keep it readable.

## Commit hygiene

- One concept per commit
- Commit messages describe the GIS or UX change, not just the file
- Don't commit `data/raw/` or `__pycache__` or `.venv`

## Model routing

This project is intentionally run in `opusplan` mode (Opus plans, Sonnet executes). When you reach a task that's clearly below Sonnet-tier — boilerplate generation, file moves, `.gitignore` entries, README polish, formatting fixes, simple find-and-replace, restating things in different words — pause and suggest the owner switch to Haiku via `/model haiku` rather than spending Sonnet tokens on it. The owner will switch back when needed.

Conversely, if you're mid-execution on Sonnet and you hit something that needs real reasoning (a CRS bug you can't explain, an architectural decision, a MapLibre expression that isn't behaving), pause and suggest switching to Opus rather than guessing.

Treat model choice as a visible, explicit decision. Don't silently power through with the wrong tier.

## When stuck

Coordinate system bugs are the most common GIS pain point. If something is rendering in the wrong place, the answer is almost always a CRS mismatch. Check the CRS of the source data, the CRS of the output, and what MapLibre expects (EPSG:4326). In that order.