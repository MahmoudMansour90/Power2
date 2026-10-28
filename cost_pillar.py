"""Cost pillar page: county-level industrial electricity price, 2001-2025
actual (EIA Form 861, now including final 2025 data, with the Louisiana
"Parish" population-join bug fixed upstream in the pipeline notebook --
Louisiana now has real county-level data every year 2001-2025) + 2026-2028
forecast. Real data only -- see data_prep.py for how data/actual.parquet,
data/forecast.parquet and data/county_lookup.parquet are produced from the
notebook's outputs.

v3.2 -- second round of fixes from real post-deployment use (see map_utils.py
module docstring for the map-level fixes: two-trace no-data redesign,
unselected-opacity fix, custom gradient legend). This file's own changes:
  - Color scale's top end is now capped at the 98th percentile of all
    county-years, not the single highest value -- one or two outlier
    county-years were crushing the rest of the map into the low (yellow)
    end of the ramp. Values above the cap are simply clamped to the
    darkest color (standard Plotly behavior), not hidden or distorted.
  - Click vs. search are now genuinely different experiences:
      * Click -> a compact, bordered card for whichever year the slider is
        CURRENTLY on (not always the latest year), with price, national
        standing, national median, reporting utilities, and national rank.
        No trend chart.
      * Search -> unchanged: always the latest actual year, the same
        metrics plus total reported volume, and the full trend chart.
  - Metric fonts rebalanced: a long explanatory phrase ("cheaper than 19%
    of U.S. counties") is no longer the giant st.metric value itself --
    the metric shows the short number, the sentence is a caption under it.

Carried over unchanged from v3.1:
  - Map is a single static choropleth per rerun, not a Plotly animation.
  - Alaska/Hawaii structurally impossible to show.
  - Year control is st.select_slider with an HTML every-2-years ruler.
  - Search is two dropdowns: State, then County (+ FIPS).
  - No mention of the specific forecast model name anywhere.
  - No download affordances anywhere.
  - No "About this data and methodology" section, no 68%/CI-level/
    likely-range numbers, no confidence grade anywhere.
"""
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from map_utils import (
    build_static_choropleth, render_year_slider, get_clicked_fips,
    render_gradient_legend, NO_DOWNLOAD_CONFIG,
)

KEY = 'cost'


@st.cache_data
def load_data():
    actual = pd.read_parquet('data/actual.parquet')
    forecast = pd.read_parquet('data/forecast.parquet')
    county_lookup = pd.read_parquet('data/county_lookup.parquet')
    return actual, forecast, county_lookup


def _all_fips_base(geo, county_lookup):
    all_fips = [str(f.get('id', '')).zfill(5) for f in geo['features']]
    base = pd.DataFrame({'FIPS': all_fips}).drop_duplicates('FIPS')
    return base.merge(county_lookup, on='FIPS', how='left')


def _year_df(base, actual, forecast, sel_year, last_actual_year):
    """One row per contiguous county for sel_year -- including counties
    with no reported value that year (left as NaN), so the map can show
    them as gray 'no data' rather than silently dropping them."""
    src = actual if sel_year <= last_actual_year else forecast
    slice_ = src[src['Year'] == sel_year]
    val_cols = [c for c in slice_.columns if c not in ('FIPS', 'State', 'County_Name')]
    return base.merge(slice_[['FIPS'] + val_cols], on='FIPS', how='left')


def _hover_text(df, is_forecast):
    tag = ' (forecast)' if is_forecast else ''
    out = []
    for _, r in df.iterrows():
        if pd.isna(r.get('Price_cents_kWh')):
            out.append(f"{r['County_Name']}, {r['State']}<br>No data reported")
        else:
            out.append(f"{r['County_Name']}, {r['State']}<br>{r['Price_cents_kWh']:.2f} ¢/kWh{tag}")
    return out


def render(geo, state_borders):
    actual, forecast, county_lookup = load_data()
    last_actual_year = int(actual['Year'].max())
    forecast_horizon_year = last_actual_year + 3
    base = _all_fips_base(geo, county_lookup)

    st.info(
        'County-level **industrial** electricity price (not retail, since data '
        f'centers are industrial loads): 2001-{last_actual_year} actual data, EIA Form 861, '
        f'with a 3-year forecast ({last_actual_year + 1}-{forecast_horizon_year}).'
    )

    # -------------------------------------------------- search (two dropdowns)
    s1, s2 = st.columns(2)
    state_options = sorted(county_lookup['State'].dropna().unique())
    sel_state = s1.selectbox(
        'State', state_options, index=None, placeholder='Select a state...', key=f'{KEY}_search_state',
    )
    if sel_state:
        county_df = county_lookup[county_lookup['State'] == sel_state].sort_values('County_Name')
        county_labels = [f"{r.County_Name} ({r.FIPS})" for r in county_df.itertuples()]
    else:
        county_labels = []
    sel_county_label = s2.selectbox(
        'County', county_labels, index=None, placeholder='Select a county...',
        key=f'{KEY}_search_county_{sel_state}',
    )

    # ---------------------------------------------------------------- map
    st.subheader("County-level industrial electricity price")

    years = list(range(2001, forecast_horizon_year + 1))
    sel_year = render_year_slider(f'{KEY}_year', years, last_actual_year, last_actual_year)
    is_forecast = sel_year > last_actual_year

    _all_prices = pd.concat([actual['Price_cents_kWh'], forecast['Price_cents_kWh']])
    vmin = _all_prices.quantile(0.02)
    vmax = _all_prices.quantile(0.98)  # capped -- see module docstring fix #3

    year_df = _year_df(base, actual, forecast, sel_year, last_actual_year)
    fig_map = build_static_choropleth(
        year_df, geo, state_borders, 'Price_cents_kWh', 'YlOrRd', vmin, vmax,
        hover_text=_hover_text(year_df, is_forecast),
    )
    event = st.plotly_chart(
        fig_map, width='stretch', key=f'{KEY}_map',
        on_select='rerun', selection_mode='points', config=NO_DOWNLOAD_CONFIG,
    )
    render_gradient_legend(
        'YlOrRd', vmin, vmax, 'Lower Price', 'Higher Price',
        value_fmt=lambda v: f"{v:.2f} ¢/kWh",
        caption=(
            f"Color scale capped at the 98th percentile ({vmax:.2f} ¢/kWh) across all "
            "counties and years so ordinary variation stays visible; a small number of "
            "higher-priced outliers above that are shown at the darkest color rather than "
            "stretching the whole scale to fit them."
        ),
    )
    st.caption(
        f"Drag the slider to any year 2001-{forecast_horizon_year}. "
        f"{last_actual_year + 1}-{forecast_horizon_year} are forecast years, not measured actuals. "
        "Click any county for a quick summary for the year shown, or search above for full detail and history."
    )

    # ---------------------------------------- resolve click vs. search intent
    click_fips = get_clicked_fips(event)
    prev_click = st.session_state.get(f'{KEY}_prev_click')
    prev_search = st.session_state.get(f'{KEY}_prev_search_val')

    sel_fips = st.session_state.get(f'{KEY}_sel_fips')
    sel_source = st.session_state.get(f'{KEY}_sel_source')

    if click_fips is not None and click_fips != prev_click:
        sel_fips, sel_source = click_fips, 'click'
        st.session_state[f'{KEY}_prev_click'] = click_fips
    search_key = (sel_state, sel_county_label)
    if sel_county_label is not None and search_key != prev_search:
        sel_fips = sel_county_label.split('(')[-1].rstrip(')')
        sel_source = 'search'
        st.session_state[f'{KEY}_prev_search_val'] = search_key

    st.session_state[f'{KEY}_sel_fips'] = sel_fips
    st.session_state[f'{KEY}_sel_source'] = sel_source

    # ============================================================ county detail
    st.divider()
    if sel_fips is None:
        st.caption('Click a county on the map, or search for one above, to see its detail.')
    else:
        _render_detail(actual, forecast, sel_fips, sel_source, sel_year, last_actual_year)

    # ======================================================== comparison table
    st.divider()
    _render_comparison(actual, forecast, last_actual_year)


def _national_rank(actual, sel_fips, year):
    """Rank among all U.S. counties with a reported price in `year`
    (1 = cheapest). Returns None if this county has no reported price that
    year. Generalized to any year, not just the latest, so the click card
    can show a rank for whichever year the slider is on."""
    year_slice = actual[actual['Year'] == year].dropna(subset=['Price_cents_kWh'])
    if year_slice.empty:
        return None
    year_slice = year_slice.sort_values('Price_cents_kWh').reset_index(drop=True)
    row = year_slice[year_slice['FIPS'] == sel_fips]
    if row.empty:
        return None
    return int(row.index[0]) + 1, len(year_slice)


def _render_metrics_block(actual, sel_fips, year):
    """The core set of metrics for one county/year: price, national
    standing, national median, reporting utilities, national rank. Used by
    BOTH the click card and the search panel, for whichever year each one
    needs -- this is what keeps their numbers consistent and keeps metric
    fonts balanced (short numeric value in st.metric, the explanatory
    sentence as a caption underneath rather than crammed into the metric
    itself)."""
    row = actual[(actual['FIPS'] == sel_fips) & (actual['Year'] == year)]
    if row.empty:
        st.metric(f'Price ({year})', 'n/a')
        st.caption('No data reported for this county in this year.')
        return
    r = row.iloc[0]
    m1, m2, m3 = st.columns(3)
    m1.metric(f'Price ({year})', f"{r['Price_cents_kWh']:.2f} ¢/kWh")
    m2.metric('National standing', f"{r['Pct_Counties_MoreExpensive_SameYear']:.0f}%")
    m2.caption(f"cheaper than {r['Pct_Counties_MoreExpensive_SameYear']:.0f}% of U.S. counties")
    m3.metric('National median price', f"{r['National_Median_Price_cents_kWh_SameYear']:.2f} ¢/kWh")
    reporting = r.get('Reporting_Utilities')
    if isinstance(reporting, str) and reporting:
        st.caption(f"Reporting utilities: {reporting}")
    rank_info = _national_rank(actual, sel_fips, year)
    if rank_info:
        rank, n_total = rank_info
        st.caption(f"National rank ({year}): **#{rank} cheapest** of {n_total:,} U.S. counties")


def _render_forecast_metrics_block(forecast, sel_fips, year):
    """Click-card metrics for a FORECAST year. Forecast rows don't carry
    national standing / reporting utilities / rank (those are only
    computed from observed data in data_prep.py), and per house rule no
    numeric CI/likely-range figure is shown anywhere -- so this is
    deliberately just the one number."""
    row = forecast[(forecast['FIPS'] == sel_fips) & (forecast['Year'] == year)]
    if row.empty:
        st.metric(f'Price ({year})', 'n/a')
        st.caption('No forecast available for this county in this year.')
        return
    r = row.iloc[0]
    st.metric(f'Price ({year}, forecast)', f"{r['Price_cents_kWh']:.2f} ¢/kWh")
    st.caption('Forecast year -- national standing, reporting utilities, and rank are only available for observed years.')


def _render_detail(actual, forecast, sel_fips, sel_source, sel_year, last_actual_year):
    a_sel = actual[actual['FIPS'] == sel_fips].sort_values('Year')
    f_sel = forecast[forecast['FIPS'] == sel_fips].sort_values('Year')
    if a_sel.empty and f_sel.empty:
        st.warning('No data for this county.')
        return
    name_row = (a_sel.iloc[-1] if not a_sel.empty else f_sel.iloc[-1])
    st.subheader(f"{name_row['County_Name']}, {name_row['State']}")

    if sel_source == 'click':
        # Compact card for whichever year the slider is CURRENTLY on --
        # not always the latest year -- and no trend chart, per the
        # confirmed click-vs-search split.
        with st.container(border=True):
            if sel_year <= last_actual_year:
                _render_metrics_block(actual, sel_fips, sel_year)
            else:
                _render_forecast_metrics_block(forecast, sel_fips, sel_year)
        return

    # -------- search: unchanged full experience, always the latest actual year
    _render_metrics_block(actual, sel_fips, last_actual_year)
    _render_search_extra(actual, sel_fips, last_actual_year)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=a_sel['Year'], y=a_sel['Price_cents_kWh'], mode='lines+markers',
                              name='Actual', line=dict(color='#1f77b4', width=2)))
    if not f_sel.empty:
        bridge_year = pd.concat([a_sel['Year'].tail(1), f_sel['Year']])
        bridge_price = pd.concat([a_sel['Price_cents_kWh'].tail(1), f_sel['Price_cents_kWh']])
        has_ci = f_sel['Upper_CI_cents_kWh'].notna().all() and f_sel['Lower_CI_cents_kWh'].notna().all()
        if has_ci:
            upper = pd.concat([a_sel['Price_cents_kWh'].tail(1), f_sel['Upper_CI_cents_kWh']])
            lower = pd.concat([a_sel['Price_cents_kWh'].tail(1), f_sel['Lower_CI_cents_kWh']])
            fig.add_trace(go.Scatter(
                x=pd.concat([bridge_year, bridge_year[::-1]]),
                y=pd.concat([upper, lower[::-1]]),
                fill='toself', fillcolor='rgba(255,127,14,0.18)',
                line=dict(color='rgba(255,255,255,0)'), hoverinfo='skip',
                name='Forecast range', showlegend=False,
            ))
        fig.add_trace(go.Scatter(x=bridge_year, y=bridge_price, mode='lines+markers',
                                  name='Forecast', line=dict(color='#ff7f0e', width=2, dash='dash'),
                                  hovertemplate='%{x}: %{y:.2f} ¢/kWh (forecast)<extra></extra>'))
    fig.update_layout(
        xaxis_title='Year', yaxis_title='Price (cents/kWh)',
        xaxis=dict(tickformat='d', dtick=1),  # a narrow year range otherwise gets fractional/comma'd ticks
        height=380, margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation='h', y=1.12), hovermode='x unified',
    )
    st.plotly_chart(fig, width='stretch', key=f'{KEY}_trend_{sel_fips}', config=NO_DOWNLOAD_CONFIG)


def _render_search_extra(actual, sel_fips, last_actual_year):
    """The one extra field shown only when the detail panel was opened via
    search (national rank moved into the shared metrics block above, so
    both click and search now show it; total reported volume remains
    search-only)."""
    year_slice = actual[actual['Year'] == last_actual_year]
    row = year_slice[year_slice['FIPS'] == sel_fips]
    if row.empty:
        return
    total_mwh = row['Total_MWh'].iloc[0]
    st.caption(f"Total reported industrial volume ({last_actual_year}): **{total_mwh:,.0f} MWh**")


def _render_comparison(actual, forecast, last_actual_year):
    st.subheader('Compare counties')
    latest_actual = (
        actual.sort_values('Year').drop_duplicates('FIPS', keep='last')
        .set_index('FIPS')
    )
    forecast_horizon_year = last_actual_year + 3
    fc_last = forecast[forecast['Year'] == forecast_horizon_year][
        ['FIPS', 'Price_cents_kWh']
    ].rename(columns={'Price_cents_kWh': 'Price_cents_kWh_forecast'})

    states = sorted(actual['State'].dropna().unique())
    c1, c2, c3 = st.columns(3)
    scope = c1.radio('Scope', ['All contiguous U.S.', 'One state'], horizontal=True, key=f'{KEY}_scope')
    sort_options = {
        f'Last reported price ({last_actual_year}, highest)': ('Price_cents_kWh_actual', False),
        f'Last reported price ({last_actual_year}, lowest)': ('Price_cents_kWh_actual', True),
        f'{forecast_horizon_year} forecast (highest)': ('Price_cents_kWh_forecast', False),
        f'{forecast_horizon_year} forecast (lowest)': ('Price_cents_kWh_forecast', True),
    }
    sort_choice = c2.selectbox('Sort by', list(sort_options.keys()), index=2, key=f'{KEY}_sort')
    n_show = c3.slider('Counties to show', 5, 50, 15, key=f'{KEY}_n')

    la = latest_actual.reset_index().rename(
        columns={'Price_cents_kWh': 'Price_cents_kWh_actual', 'Year': 'Last_Year'})
    table = la.merge(fc_last, on='FIPS', how='left')

    if scope == 'One state':
        sel_state = st.selectbox('State', states, index=states.index('MO') if 'MO' in states else 0, key=f'{KEY}_cmp_state')
        table = table[table['State'] == sel_state]

    col, asc = sort_options[sort_choice]
    table = table.sort_values(col, ascending=asc, na_position='last').head(n_show)

    st.dataframe(
        table[['FIPS', 'State', 'County_Name', 'Last_Year', 'Price_cents_kWh_actual',
               'Pct_Counties_MoreExpensive_SameYear', 'Price_cents_kWh_forecast']]
        .rename(columns={
            'Last_Year': 'Last reported year',
            'Price_cents_kWh_actual': f'Last reported price (¢/kWh)',
            'Pct_Counties_MoreExpensive_SameYear': 'Cheaper than % of U.S. counties',
            'Price_cents_kWh_forecast': f'{forecast_horizon_year} Forecast (¢/kWh)',
        }).round(2),
        width='stretch', hide_index=True,
    )
