# Power Risk Index for Data Center Construction Planning (v3.2)

MOCCI -- interactive Cost and Reliability pillar explorer, built on real EIA-861
data through 2025. Availability (Capacity) and the Composite Power Risk Index
are shown as honest placeholders -- no synthetic or invented numbers for
either, until those pillars have real, validated results.

One page, one URL, with a tab per pillar (Cost / Reliability / Availability /
Composite) -- no separate page URLs to navigate between.

## v3.2 -- data fix + second map/UI bug-fix round, from real post-deployment use

**Louisiana data gap fixed at the source.** Louisiana counties were
completely missing from the Cost pillar for 2001-2008 (visible on the map as
all-gray for those years) -- this was a real pipeline bug, not an EIA data
gap, confirmed by tracing it with real data: Louisiana is the only U.S.
state whose Census population-file county names end in "Parish" instead of
"County", and the pipeline's population-key cleanup only ever stripped the
"County" suffix. Every Louisiana county's population join silently failed
for those years, which zeroed out its allocated volume and dropped it from
the final output. Fixed with a one-line change in the frozen pipeline
notebook (strip "Parish" too); the pipeline was rerun end-to-end and the
corrected output was independently re-verified against EIA's own published
totals (within 0.01-0.3%) before being loaded into this app. Louisiana now
has real county-level data every year, 2001-2025.

**Map legend, color scale, no-data handling, and click behavior reworked,**
fixing four real bugs the user found using v3.1 for real:

- **The color legend no longer starts with gray, and most counties no
  longer look the same washed-out yellow.** Root cause: the old single-trace
  map reserved a gray band at the bottom of the SAME color ramp real data
  was drawn from (via a sentinel value below the lowest real value), and
  used the single highest value anywhere in the dataset -- a rare outlier --
  as the top of that ramp, crushing ordinary counties into its low end.
  Fixed by splitting the map into two independent Choropleth traces (real
  data vs. no-data), so gray is never part of the real-data ramp at all, and
  by capping the Cost scale's top end at the 98th percentile across all
  counties and years (a handful of outliers above that are simply shown at
  the darkest color, not hidden). Reliability's scale was already a fixed
  0-100 and needed no change.
- **Real values are no longer ever shown as gray "no data."** Root cause:
  the old sentinel approach compared every value against one global floor
  computed across ALL years combined, so a real but relatively low value in
  an early year (confirmed: 19 of 23 Wyoming counties in 2003) could fall
  below that floor and land in the reserved gray band, indistinguishable
  from genuinely missing counties. The two-trace split removes this
  possibility structurally -- a real value is simply never compared against
  a sentinel at all.
- **A new custom legend** (replacing Plotly's native colorbar, which is
  turned off entirely now) matches the reference design: a horizontal
  gradient bar labeled "Lower Price"/"Higher Price" (Cost) or "Lower
  Risk"/"Higher Risk" (Reliability), numeric endpoint values underneath, and
  a separate gray "No data reported" swatch below that, with a short italic
  caption. The Reliability caption describes CRI honestly as a constructed
  0-100 index, not "Jenks natural breaks" -- that phrasing (seen in an
  earlier reference image) doesn't match how CRI is actually computed.
- **Clicking a county no longer dims the whole map.** Root cause: Plotly's
  default behavior is to fade every unselected point once any point is
  selected. Fixed with an explicit "stay fully visible whether selected or
  not" setting on every map trace.

**Click and search are now genuinely different experiences**, resolving the
earlier open question about how they should relate:
- **Click** a county -> a compact, clearly bordered card appears below the
  map with that county's price/CRI, national standing, national median,
  reporting utilities, and national rank **for whichever year the slider is
  currently on** (not always the latest year) -- no trend chart.
- **Search** for a county (the two dropdowns above the map) -> the full
  experience: the same metrics for the latest actual/observed year, plus
  total reported volume (Cost), the full historical + forecast trend chart,
  and (Reliability) the SAIDI/SAIFI history expander.

**Metric fonts rebalanced.** A long explanatory phrase (e.g. "more reliable
than 19% of counties") is no longer rendered at the same oversized font as a
short number -- metrics now show a short value (e.g. "19%") with the
explanatory sentence as a smaller caption underneath.

**Removed:** the "Years of CRI history" line, per explicit request.

## v3.1 -- map rework, fixing real bugs found after deploying v3

After v3 was deployed and tested for real, the map had genuine bugs that
this sandbox's own testing could never have caught (its map rendering could
not be visually verified here at all -- see "A verification note on the
maps" below, carried over from v3). Every one of these is fixed by
rebuilding the map on a different architecture, not patched:

- **State borders no longer mask the county data or block clicks.** Root
  cause: the map was a Plotly *animation* (one frame per year); only the
  very first frame actually carried the county geometry, so every other
  year rendered no county shapes at all -- and nothing to click. The map is
  now a single static choropleth, fully rebuilt on every rerun when the
  year changes. There is no animation anywhere anymore.
- **Alaska and Hawaii are now structurally impossible to show**, not just
  cropped out of view. Root cause: Plotly's `scope='usa'` basemap draws
  AK/HI inset boxes as a fixed part of that basemap, regardless of any
  view-window cropping. That basemap is now turned off entirely
  (`visible=False`); the map shows only our own county choropleth and our
  own state-border lines (dissolved from the same AK/HI-free county
  geometry in `data_prep.py`'s `build_state_borders()`). With no AK/HI
  geometry anywhere in either trace, there's nothing left to draw.
- **Search is back to two dropdowns** -- State, then County (with its
  FIPS) -- replacing the single combined search box.
- **The detail panel always shows the latest actual/observed year**,
  regardless of which year the map slider is on, and regardless of whether
  it was opened by a map click or by searching.
- **The year slider marks every 2 years** (not every single year) with a
  small ruler under the slider, and **forecast-year labels are colored
  differently** from actual-year labels. Every single year is still
  individually selectable via the slider itself -- the ruler is a visual
  guide alongside it.
- **No mention of the specific forecast model's name** anywhere in the UI.
- **No download affordances anywhere** -- chart image export is removed
  from every chart's toolbar, and table CSV/clipboard export is disabled
  app-wide (`.streamlit/config.toml`).

## What was new in v3 (still true in v3.1)

- **2025 data included.** Cost now runs 2001-2025 with a 2026-2028 forecast;
  Reliability now runs 2013-2025 with a 2026-2028 projection.
- **Cost now carries `Reporting_Utilities`** (utility names serving each
  county-year, largest first), matching Reliability's existing convention.
- **Contiguous U.S. only.**
- **Thicker, darker state borders** (now the app's own line trace -- see above).
- **No "About this data and methodology" section anywhere** -- removed per
  request; backtest scorecards, disclosures, and the CRI 100-ceiling
  explanation are gone from the UI.
- **No 68%/CI-level/likely-range/probability numbers shown anywhere** -- not
  in the hover tooltip, the click panel, or the search panel. Forecast years
  are tagged "(forecast)" only. The shaded uncertainty band stays on the
  trend chart as a visual, with no numeric label attached to it.
- **No confidence grade shown anywhere**, and the "no data" legend is a
  single short line ("Gray = not available (no reporting).").
- **Map click and county search open the same detail panel**, always at the
  latest actual/observed year (see v3.1 above). Search additionally shows a
  couple of extra fields (national rank, total volume / years of history)
  that the click panel does not.
- **National comparison stat added for Cost** (`Pct_Counties_MoreExpensive_SameYear`,
  computed once in `data_prep.py`), mirroring Reliability's own pre-computed
  `Pct_Counties_Less_Reliable_SameYear`. Both are scoped to observed years only.

## What's in this folder

- `app.py` -- main entry point: password gate, header, scope banner, tabs
- `cost_pillar.py`, `reliability_pillar.py` -- each real pillar's page, as
  its own module so they stay easy to work on independently
- `availability_pillar.py`, `composite_pillar.py` -- honest "not yet
  available" placeholders
- `map_utils.py` -- shared choropleth styling: the static (non-animated)
  per-rerun choropleth (built as two separate traces -- real data and "no
  data" -- see v3.2 above), the app's own state-border line trace, the
  every-2-years year ruler, click-to-FIPS resolution, the custom HTML
  gradient legend, and the click-dimming fix -- used by both real pillars'
  maps
- `data_prep.py` -- regenerates the files in `data/` from each pillar's
  notebook outputs (run this again whenever a pillar's underlying data is
  refreshed) -- see the top of that file for the exact input filenames.
  Also dissolves the county boundary file into `state_borders.json` (see
  `build_state_borders()`).
- `data/` -- the static data snapshot the app actually loads: parquet files
  per pillar, plus `counties_fips.json` (contiguous-US-only county boundary
  file, includes Connecticut's 2022+ planning regions) and
  `state_borders.json` (per-state boundary lines, dissolved from the same
  county file)
- `assets/mocci_logo.png` -- the MOCCI logo (password screen + header)
- `.streamlit/secrets.toml.example` -- template for the password secret
- `.streamlit/config.toml` -- disables table CSV/clipboard export app-wide
- `requirements.txt`

## Password protection

Gated by a single shared password, checked against `st.secrets["app_password"]`.
The real password is never stored in this folder or in source control --
only `secrets.toml.example` (a template) is included.

**Local run:** copy `.streamlit/secrets.toml.example` to
`.streamlit/secrets.toml` and put a real password in it. That file is
already in `.gitignore`.

**Streamlit Community Cloud:** no `secrets.toml` file needed in the repo.
After deploying, go to the app's **Settings -> Secrets** and paste:
```
app_password = "your real password here"
```

## Deploy to Streamlit Community Cloud

1. Create a new GitHub repository and push everything in this folder to it
   (the `data/` folder and logo included).
2. Go to https://share.streamlit.io/, connect your GitHub account.
3. Select the repository, branch `main`, main file path `app.py`, deploy.
4. Set the password in the app's Secrets before sharing the link.

## Run locally

```
pip install -r requirements.txt
streamlit run app.py
```

## Updating a pillar's data later

Each pillar's notebook is the source of truth; this app never recomputes
anything, only reshapes and displays what the notebook already validated.

1. Rerun the relevant pillar's notebook, producing fresh output files.
2. Place those fresh files alongside `data_prep.py` (see the paths at the
   top of that script).
3. Run `python3 data_prep.py` -- it regenerates every file in `data/`.
4. Commit and push the updated `data/` files. Streamlit Community Cloud
   redeploys automatically.

## A verification note on the maps

Every Plotly geo trace (`go.Choropleth`, `go.Scattergeo`, any
`projection_type`) fetches a base topology file from `cdn.plot.ly` at
render time, in the browser -- confirmed directly in this rebuild: the
request fires the same way for `'albers usa'` and for `'mercator'`, and
even with the basemap turned off (`visible=False`). This is how Plotly's
geo module works for every deployment, not something specific to this app.
In the sandboxed environment this app was built in, that CDN host is
blocked by the sandbox's own network policy, so **the map itself (the
colored county shapes and the state-border lines) could not be rendered or
visually inspected there, in v3, v3.1, or this v3.2 round.** This is the
same limitation disclosed in v3's README; it is unrelated to -- and not an
explanation for -- the bugs the user found after deploying v3/v3.1, which
were real code bugs (see the v3.2 and v3.1 sections above) now fixed and
verified by other means:

- **`build_static_choropleth()`'s two-trace split** (the real-data trace vs.
  the no-data trace, and the click-dimming fix) was unit-tested directly in
  Python against synthetic data for three cases -- a mix of real and
  missing counties, all-real, and all-missing -- confirming it builds a
  valid figure with the right trace count and `unselected`/`selected`
  marker opacity in every case, independent of rendering.
- **The custom HTML gradient legend** was verified by running the app live
  (see below) and reading its rendered text and gradient CSS directly --
  correct low/high labels, correct percentile-capped numeric endpoints, the
  separate no-data swatch, and the honest (non-"Jenks") Reliability caption
  all confirmed present.
- **The click-vs-search split** was verified directly against the app's
  real data (not just read, but exercised) using Streamlit's own
  `AppTest` framework, which runs the actual app script and reads back its
  real output -- for both pillars, for a clicked historical year, and for a
  clicked forecast year: confirming the click card shows the metrics for
  the year actually selected (not always the latest), degrades correctly
  for forecast years (no national-standing/reporting/rank fields, since
  those aren't computed for forecast rows), never renders a trend chart or
  the SAIDI/SAIFI expander, and that the search path still does render both
  -- all with zero Python exceptions anywhere in any of those paths.
- The **state-border dissolution** (`build_state_borders()`) was verified
  visually offline with matplotlib (no CDN dependency) -- a clean,
  recognizable, AK/HI-free contiguous-US outline.
- Everything else that doesn't depend on the geo trace rendering -- the
  year slider and its every-2-years/forecast-colored ruler, the
  two-dropdown search, the comparison table -- was verified directly in a
  running instance of this app, including confirming no Python traceback
  occurs anywhere in that flow.

**What to confirm once deployed (or running locally with real network
access):** the map renders visible, contiguous-US-only county shapes;
Alaska/Hawaii do not appear anywhere, including no empty inset boxes; state
borders read clearly and no longer sit on top of / block the county colors;
a map click on any year (not just the default) opens the correct county's
detail panel; the year ruler's every-2-years marks and forecast-year
coloring look right under the slider; and no download icon appears on any
chart or table.

## Adding the Availability pillar or the Composite index later

Follow the same pattern as Cost and Reliability: once that pillar has a
validated notebook output, extend `data_prep.py` to export it, write a new
`availability_pillar.py` (or replace the composite placeholder) following
`reliability_pillar.py` as the template, and wire it into the matching tab
in `app.py` in place of the current placeholder import.
