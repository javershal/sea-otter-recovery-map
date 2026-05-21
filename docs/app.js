// Years with data — 2011 was skipped by USGS, no census conducted
const YEARS = Array.from({ length: 33 }, (_, i) => 1985 + i).filter(y => y !== 2011);
const LAST_IDX = YEARS.length - 1;

// Central CA coast: frames Monterey Bay through Point Conception
const MAP_CENTER = [-121.8, 36.2];
const MAP_ZOOM = 7.5;

// lin_dens ramp: transparent at zero → teal → bright seafoam at peak
// Colors drawn from MBA palette: kelp, ocean surface, bioluminescent shallows
const DENSITY_COLOR = [
  'interpolate', ['linear'],
  ['get', 'lin_dens'],
  0,  'rgba(0,   120, 130, 0)',
  2,  'rgba(0,   165, 160, 0.52)',
  5,  'rgba(0,   195, 180, 0.70)',
  10, 'rgba(80,  220, 195, 0.84)',
  18, 'rgba(185, 245, 225, 0.93)',
];

let currentIdx = 0;
let playTimer = null;
let statsByYear = {}; // precomputed at load: { year: { peak, avg } }

// ── Map init ────────────────────────────────────────────────────────────────
const map = new maplibregl.Map({
  container: 'map',
  // Carto Dark Matter: deep navy ocean basemap, free, no API key
  style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
  center: MAP_CENTER,
  zoom: MAP_ZOOM,
  attributionControl: { compact: true },
});

map.addControl(new maplibregl.NavigationControl(), 'top-left');

// ── Load data and add layers ─────────────────────────────────────────────────
map.on('load', async () => {
  // Fetch all three GeoJSON files in parallel
  const census = await fetch('data/census_summary.geojson').then(r => r.json());

  // Precompute peak + avg lin_dens per year so scrubbing is an O(1) lookup
  statsByYear = buildStats(census.features);

  // ── Sources ──────────────────────────────────────────────────────────────
  map.addSource('census', { type: 'geojson', data: census });

  // ── Census summary layer — filled polygons colored by dens_sm ────────────
  // dens_sm = otters per square mile; drives the color ramp above
  map.addLayer({
    id: 'census-fill',
    type: 'fill',
    source: 'census',
    filter: ['==', ['get', 'year'], YEARS[0]],
    paint: {
      'fill-color': DENSITY_COLOR,
      'fill-opacity': 1,
    },
  });

  // ── Tooltip on census polygons ────────────────────────────────────────────
  const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });

  map.on('mousemove', 'census-fill', e => {
    map.getCanvas().style.cursor = 'crosshair';
    const props = e.features[0].properties;
    popup.setLngLat(e.lngLat)
      .setHTML(`<strong>${props.lin_dens?.toFixed(1) ?? '—'}</strong> otters / linear mi`)
      .addTo(map);
  });

  map.on('mouseleave', 'census-fill', () => {
    map.getCanvas().style.cursor = '';
    popup.remove();
  });

  updatePanel(YEARS[0]);
});

// ── Year update ──────────────────────────────────────────────────────────────
function updateYear(idx) {
  currentIdx = idx;
  const year = YEARS[idx];

  // Swap visibility on all layers by changing the year filter
  const yearFilter = ['==', ['get', 'year'], year];
  if (map.getLayer('census-fill')) map.setFilter('census-fill', yearFilter);

  // Sync scrubber UI
  document.getElementById('year-slider').value = idx;
  document.getElementById('year-label').textContent = year;
  document.getElementById('panel-year').textContent = year;
  updatePanel(year);
}

// Walk all features once at load time and bucket stats by year
function buildStats(features) {
  const acc = {};
  for (const f of features) {
    const { year, lin_dens } = f.properties;
    if (lin_dens == null || !isFinite(lin_dens)) continue;
    if (!acc[year]) acc[year] = { peak: -Infinity, sum: 0, count: 0 };
    if (lin_dens > acc[year].peak) acc[year].peak = lin_dens;
    acc[year].sum += lin_dens;
    acc[year].count += 1;
  }
  const stats = {};
  for (const [year, { peak, sum, count }] of Object.entries(acc)) {
    stats[year] = { peak, avg: sum / count };
  }
  return stats;
}

// O(1) lookup — no iteration at scrub time
function updatePanel(year) {
  const s = statsByYear[year];
  document.getElementById('panel-peak').textContent = s ? s.peak.toFixed(1) : '—';
  document.getElementById('panel-avg').textContent  = s ? s.avg.toFixed(1)  : '—';
}

// ── Scrubber controls ────────────────────────────────────────────────────────
document.getElementById('year-slider').addEventListener('input', e => {
  stopPlay();
  updateYear(Number(e.target.value));
});

document.getElementById('play-btn').addEventListener('click', () => {
  if (playTimer) {
    stopPlay();
  } else {
    startPlay();
  }
});

function startPlay() {
  // If we're at the end, rewind to start before playing
  if (currentIdx >= LAST_IDX) updateYear(0);
  document.getElementById('play-btn').textContent = '❚❚';
  playTimer = setInterval(() => {
    if (currentIdx >= LAST_IDX) {
      stopPlay();
      return;
    }
    updateYear(currentIdx + 1);
  }, 800);
}

function stopPlay() {
  clearInterval(playTimer);
  playTimer = null;
  document.getElementById('play-btn').textContent = '▶';
}

// ── Mobile drawer toggle ─────────────────────────────────────────────────────
document.getElementById('drawer-toggle').addEventListener('click', () => {
  const sidebar = document.getElementById('sidebar');
  const isOpen = sidebar.classList.toggle('open');
  document.getElementById('drawer-toggle').setAttribute('aria-expanded', isOpen);
});
