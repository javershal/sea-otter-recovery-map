# Sea Otter Recovery Map

An interactive map of southern sea otter (*Enhydra lutris nereis*) population and range along the California coast from 1985 to 2017. Drag the year scrubber to watch a population recover from near-extinction.

![status: in development](https://img.shields.io/badge/status-in_development-yellow)

## The story

By the early 1900s, the southern sea otter was nearly extinct — hunted to roughly 50 surviving animals along a remote stretch of the Big Sur coast. Federal protection began in 1911. By 1985, when the modern annual census started, the population had crept back to around 1,200 animals along a thin coastal strip from Half Moon Bay to Cambria.

This map shows what happened over the following three decades. Otters pushing north toward Pigeon Point and south past Point Conception. A separate dramatic recolonization of Elkhorn Slough. A 2016 milestone when the official population index first crossed 3,090 — the threshold suggested for Endangered Species Act delisting.

## Data

All data comes from the U.S. Geological Survey's annual California sea otter census, conducted cooperatively with the California Department of Fish and Wildlife, the U.S. Fish and Wildlife Service, and the Monterey Bay Aquarium. Surveys combine shore-based spotting-scope counts with low-altitude aerial counts along roughly 375 miles of California coast.

The map uses three layers per year:

- **Density polygons** — coast segments colored by otters per km² of habitat
- **Range extent** — the official northern and southern boundaries of the population
- **Extra-limit observations** — individual otters spotted outside the official range, often males pushing into new territory

Coverage runs 1985–2017. Methodology shifted after 2017 due to COVID, weather, and equipment issues, so subsequent years aren't directly comparable. USGS is developing a new statistical model expected to release in 2026 that will reconcile the full record.

Source: [USGS California Sea Otter Surveys and Research](https://www.usgs.gov/centers/werc/science/california-sea-otter-surveys-and-research)

## Running locally

You need Python 3.11+ and [uv](https://docs.astral.sh/uv/) for the preprocessing pipeline, plus any modern browser for the frontend.

```bash
# Install Python dependencies
uv sync

# Download raw shapefiles from USGS (one-time, ~50MB)
uv run scripts/download.py

# Inspect the data (recommended first run — prints CRS, columns, sample rows)
uv run scripts/inspect.py

# Preprocess into web-ready GeoJSON
uv run scripts/preprocess.py

# Serve the frontend
cd docs && python -m http.server 8000
```

Then open <http://localhost:8000>.

## Project structure

```
otter-recovery/
├── data/
│   ├── raw/              # downloaded shapefiles (gitignored)
│   └── processed/        # intermediate outputs
├── scripts/
│   ├── download.py       # fetch USGS data
│   ├── inspect.py        # exploratory data inspection
│   └── preprocess.py     # reproject, simplify, merge to GeoJSON
├── docs/
│   ├── index.html        # the map
│   ├── style.css
│   ├── app.js            # MapLibre setup, scrubber, layer filtering
│   └── data/             # generated GeoJSON consumed by the map
├── CLAUDE.md             # notes for AI-assisted development
└── README.md
```

## Tech

- **Preprocessing**: Python, GeoPandas, Shapely, pyogrio
- **Frontend**: vanilla JS, MapLibre GL JS (CDN), no build step
- **Hosting**: GitHub Pages / Cloudflare Pages (any static host)

No backend. No database. No tile server.

## What I learned building this

*(Filled in as the project progresses.)*

- 
- 
- 

## Roadmap

- [ ] v1: scrubbable 1985–2017 timeline with three layers
- [ ] Light annotations for key years (sea star wasting 2013, ESA threshold crossed 2016)
- [ ] Phase 2: real-time iNaturalist sightings overlay (last 30 days, multiple species)
- [ ] Phase 2: Elkhorn Slough zoomed inset showing the slough's own recolonization timeline

## Credits

- Census data: U.S. Geological Survey, Western Ecological Research Center
- Long-time census lead: Brian B. Hatfield (USGS)
- Statistical lead: M. Tim Tinker (USGS)
- Built with [Claude Code](https://claude.com/claude-code) as a GIS learning project

## License

Code: MIT. Census data: U.S. Government work, public domain.
