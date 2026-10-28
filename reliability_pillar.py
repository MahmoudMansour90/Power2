"""Reliability pillar page: County Reliability Index (CRI), 2013-2025
history (now including final 2025 EIA-861 data) + 2026-2028 projection.
Real data only -- see data_prep.py and the MOCCI_Reliability_Export v3
handoff note for how these files were produced and validated. The app
never recomputes anything the notebook already computed.

v3.2 -- second round of fixes from real post-deployment use (see map_utils.py
module docstring for the map-level fixes: two-trace no-data redesign,
unselected-opacity fix, custom gradient legend -- this pillar's CRI scale is
already fixed 0-100 by definition, so there's no percentile cap needed
here, unlike Cost). This file's own changes:
  - Click vs. search are now genuinely different experiences:
      * Click -> a compact, bordered card for whichever year the slider is
        CURRENTLY on (not always the latest year), with CRI, national
        standing, national median SAIDI, reporting utilities, and national
        rank. No trend chart, no SAIDI/SAIFI expander.
      * Search -> unchanged: always the latest observed year, the same
        metrics, and the full trend chart + SAIDI/SAIFI expander.
  - Removed "Years of CRI history" entirely, per explicit request --
    national rank moved into the shared metrics block used by both click
    and search, so it's no longer the only reason to keep a search-only
    extra-fields function around.
  - Metric fonts rebalanced: a long explanatory phrase ("more reliable
    than 19% of counties") is no longer the giant st.metric value itself --
    the metric shows the short percentage, the sentence is a caption
    under it.

Carried over unchanged from v3.1:
  - Map is a single static choropleth per rerun, not a Plotly animation.
  - Alaska/Hawaii structurally impossible to show.
  - Year control is st.select_slider with an HTML every-2-years ruler.
  - Search is two dropdowns: State, then County (+ FIPS).
  - No "About this data and methodology" section anywhere (backtest
    scorecard, disclosures, the 100-ceiling explanation are all removed).
  - No confidence grade, no reporting-utility COUNT, no trend label, no
    Projected_CRI_Raw anywhere -- per the handoff's own "do not show" list.
  - No 68%/likely-range/probability-band numbers shown anywhere -- forecast
    years are tagged "(forecast)" only. The shaded band stays on the trend
    chart as a visual only, with no numeric label.
"""
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from map_utils import (
    build_static_choropleth, render_year_slider, get_clicked_fips,
    render_gradient_legend, NO_DOWNLOAD_CONFIG,
)

KEY = 'rel'


@st.cache_data
def load_data():
    panel = pd.read_parquet('data/reliability_panel.parquet')
    forecast = pd.read_parquet('data/reliability_forecast.parquet')
    not_projected = pd.read_parquet('data/reliability_not_projected.parquet')
    latest_gaps = pd.read_parquet('data/reliability_latest_year_gaps.parquet')
    county_lookup = pd.read_parquet('data/reliability_county_lookup.parquet')
    return panel, forecast, not_projected, latest_gaps, county_lookup


def _all_fips_base(geo, county_lookup):
    all_fips = [str(f.get('id', '')).zfill(5) for f in geo['features']]
    base = pd.DataFrame({'FIPS': all_fips}).drop_duplicates('FIPS')
    return base.merge(county_lookup, on='FIPS', how='left')


def _year_df(base, panel, forecast, sel_year, last_observed_year):
    """One row per contiguous county for sel_year, including counties
    with no CRI value that year (left as NaN -> shown as gray 'no data')."""
    if sel_year <= last_observed_year:
        slice_ = panel[panel['Year'] == sel_year][['FIPS', 'CRI', 'CRI_Tier']].rename(
            columns={'CRI': 'CRI_value'})
    else:
        slice_ = forecast[forecast['Year'] == sel_year][
            ['FIPS', 'Projected_CRI', 'CRI_Display', 'Projected_Tier']
        ].rename(columns={'Projected_CRI': 'CRI_value'})
    return base.merge(slice_, on='FIPS', how='left')


def _hover_text(df, is_forecast):
    out = []
    for _, r in df.iterrows():
        name = str(r['County_Name']).title() if pd.notna(r.get('County_Name')) else ''
        if pd.isna(r.get('CRI_value')):
            out.append(f"{name}, {r['State']}<br>No data reported")
        elif is_forecast:
            tier = r.get('Projected_Tier', '')
            out.append(f"{name}, {r['State']}<br>CRI: {r.get('CRI_Display', r['CRI_value'])} ({tier}) (forecast)")
        else:
            tier = r.get('CRI_Tier', '')
            out.append(f"{name}, {r['State']}<br>CRI: {r['CRI_value']:.1f} ({tier})")
    return out


def render(geo, state_borders):
    panel, forecast, not_projected, latest_gaps, county_lookup = load_data()
    last_observed_year = int(panel['Year'].max())
    forecast_horizon_year = last_observed_year + 3
    not_projected_fips = set(not_projected['FIPS'])
    gaps_by_fips = latest_gaps.set_index('FIPS')['Reason'].to_dict()
    base = _all_fips_base(geo, county_lookup)

    st.info(
        'County Reliability Index (CRI): a 0-100 constructed index from EIA Form 861 '
        f'SAIDI/SAIFI outage data, county-level, 2013-{last_observed_year}, with a 3-year projection '
        f'({last_observed_year + 1}-{forecast_horizon_year}). **Higher CRI = worse reliability.**'
    )

    # -------------------------------------------------- search (two dropdowns)
    s1, s2 = st.columns(2)
    state_options = sorted(county_lookup['State'].dropna().unique())
    sel_state = s1.selectbox(
        'State', state_options, index=None, placeholder='Select a state...', key=f'{KEY}_search_state',
    )
    if sel_state:
        county_df = county_lookup[county_lookup['State'] == sel_state].sort_values('County_Name')
        county_labels = [f"{r.County_Name.title()} ({r.FIPS})" for r in county_df.itertuples()]
    else:
        county_labels = []
    sel_county_label = s2.selectbox(
        'County', county_labels, index=None, placeholder='Select a county...',
        key=f'{KEY}_search_county_{sel_state}',
    )

    # ---------------------------------------------------------------- map
    st.subheader("County Reliability Index (CRI)")
    vmin, vmax = 0, 100  # fixed per the handoff -- same scale every year, no percentile cap needed

    years = list(range(2013, forecast_horizon_year + 1))
    sel_year = render_year_slider(f'{KEY}_year', years, last_observed_year, last_observed_year)
    is_forecast = sel_year > last_observed_year

    year_df = _year_df(base, panel, forecast, sel_year, last_observed_year)
    fig_map = build_static_choropleth(
        year_df, geo, state_borders, 'CRI_value', 'OrRd', vmin, vmax,
        hover_text=_hover_text(year_df, is_forecast),
    )
    event = st.plotly_chart(
        fig_map, width='stretch', key=f'{KEY}_map',
        on_select='rerun', selection_mode='points', config=NO_DOWNLOAD_CONFIG,
    )
    render_gradient_legend(
        'OrRd', vmin, vmax, 'Lower Risk', 'Higher Risk',
        value_fmt=lambda v: f"{v:.0f}",
        caption=(
            "CRI is a constructed 0-100 index, the same scale every year (not binned "
            "into natural-break classes) -- darker = higher CRI = worse reliability."
        ),
    )
    st.caption(
        f"Drag the slider to any year 2013-{forecast_horizon_year}. "
        f"{last_observed_year + 1}-{forecast_horizon_year} are projected years, not measured actuals. "
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
        _render_detail(panel, forecast, not_projected_fips, gaps_by_fips,
                        sel_fips, sel_source, sel_year, last_observed_year)

    # ======================================================== comparison table
    st.divider()
    _render_comparison(panel, forecast, last_observed_year)


def _national_rank(panel, sel_fips, year):
    """Rank among all U.S. counties with a reported CRI in `year`
    (1 = most reliable). Returns None if this county has no CRI that year.
    Generalized to any year, not just the latest, so the click card can
    show a rank for whichever year the slider is on."""
    year_slice = panel[panel['Year'] == year].dropna(subset=['CRI'])
    if year_slice.empty:
        return None
    year_slice = year_slice.sort_values('CRI').reset_index(drop=True)  # lowest CRI = most reliable = rank 1
    row = year_slice[year_slice['FIPS'] == sel_fips]
    if row.empty:
        return None
    return int(row.index[0]) + 1, len(year_slice)


def _render_metrics_block(panel, sel_fips, year, gaps_by_fips, last_observed_year):
    """The core set of metrics for one county/year: CRI, national
    standing, national median SAIDI, reporting utilities, national rank.
    Used by BOTH the click card and the search panel, for whichever year
    each one needs -- this is what keeps their numbers consistent and
    keeps metric fonts balanced (short numeric value in st.metric, the
    explanatory sentence as a caption underneath rather than crammed into
    the metric itself)."""
    row = panel[(panel['FIPS'] == sel_fips) & (panel['Year'] == year)]
    if row.empty or pd.isna(row.iloc[0]['CRI']):
        st.metric(f'CRI ({year})', f'No {year} data')
        reason = gaps_by_fips.get(sel_fips) if year == last_observed_year else None
        st.caption(reason or 'No data reported for this county in this year.')
        return
    r = row.iloc[0]
    m1, m2, m3 = st.columns(3)
    m1.metric(f'CRI ({year})', f"{r['CRI']:.1f}", r['CRI_Tier'])
    m2.metric('National standing', f"{r['Pct_Counties_Less_Reliable_SameYear']:.0f}%")
    m2.caption(f"more reliable than {r['Pct_Counties_Less_Reliable_SameYear']:.0f}% of counties")
    m3.metric('National median SAIDI', f"{r['National_Median_SAIDI_SameYear']:.1f} min/cust")
    reporting = r.get('Reporting_Utilities')
    if isinstance(reporting, str) and reporting:
        st.caption(f"Reporting utilities: {reporting}")
    rank_info = _national_rank(panel, sel_fips, year)
    if rank_info:
        rank, n_total = rank_info
        st.caption(f"National rank ({year}): **#{rank} most reliable** of {n_total:,} U.S. counties")


def _render_forecast_metrics_block(forecast, sel_fips, year):
    """Click-card metrics for a FORECAST year. Forecast rows don't carry
    national standing / reporting utilities / rank (those are only
    computed from observed data in data_prep.py), and per house rule no
    numeric likely-range figure is shown anywhere -- so this is
    deliberately just CRI and tier."""
    row = forecast[(forecast['FIPS'] == sel_fips) & (forecast['Year'] == year)]
    if row.empty:
        st.metric(f'CRI ({year})', 'n/a')
        st.caption('No projection available for this county in this year.')
        return
    r = row.iloc[0]
    st.metric(f'Projected CRI ({year})', str(r.get('CRI_Display', r['Projected_CRI'])), r.get('Projected_Tier', ''))
    st.caption('Forecast year -- national standing, reporting utilities, and rank are only available for observed years.')


def _render_detail(panel, forecast, not_projected_fips, gaps_by_fips,
                    sel_fips, sel_source, sel_year, last_observed_year):
    p_sel = panel[panel['FIPS'] == sel_fips].sort_values('Year')
    f_sel = forecast[forecast['FIPS'] == sel_fips].sort_values('Year')
    if p_sel.empty and f_sel.empty:
        st.warning('No data for this county.')
        return
    name_row = (p_sel.iloc[-1] if not p_sel.empty else f_sel.iloc[-1])
    st.subheader(f"{name_row['County_Name'].title()}, {name_row['State']}")

    if sel_source == 'click':
        # Compact card for whichever year the slider is CURRENTLY on --
        # not always the latest year -- and no trend chart/expander, per
        # the confirmed click-vs-search split.
        with st.container(border=True):
            if sel_year <= last_observed_year:
                _render_metrics_block(panel, sel_fips, sel_year, gaps_by_fips, last_observed_year)
            else:
                _render_forecast_metrics_block(forecast, sel_fips, sel_year)
            if sel_fips in not_projected_fips and sel_year > last_observed_year:
                st.caption('Note: this county has too little history for a 3-year projection.')
        return

    # -------- search: unchanged full experience, always the latest observed year
    _render_metrics_block(panel, sel_fips, last_observed_year, gaps_by_fips, last_observed_year)
    if sel_fips in not_projected_fips:
        st.caption('Note: this county has too little history for a 3-year projection.')

    p_sel_valid = p_sel.dropna(subset=['CRI'])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=p_sel['Year'], y=p_sel['CRI'], mode='lines+markers',
                              name='Observed', line=dict(color='#1f77b4', width=2),
                              connectgaps=False))
    if not f_sel.empty and not p_sel_valid.empty:
        bridge_year = pd.concat([p_sel_valid['Year'].tail(1), f_sel['Year']])
        bridge_cri = pd.concat([p_sel_valid['CRI'].tail(1), f_sel['Projected_CRI']])
        has_ci = f_sel['CRI_Low_68'].notna().all() and f_sel['CRI_High_68'].notna().all()
        if has_ci:
            upper = pd.concat([p_sel_valid['CRI'].tail(1), f_sel['CRI_High_68']])
            lower = pd.concat([p_sel_valid['CRI'].tail(1), f_sel['CRI_Low_68']])
            fig.add_trace(go.Scatter(
                x=pd.concat([bridge_year, bridge_year[::-1]]),
                y=pd.concat([upper, lower[::-1]]),
                fill='toself', fillcolor='rgba(227,74,51,0.18)',
                line=dict(color='rgba(255,255,255,0)'), hoverinfo='skip',
                name='Forecast range', showlegend=False,
            ))
        fig.add_trace(go.Scatter(x=bridge_year, y=bridge_cri, mode='lines+markers',
                                  name='Projected', line=dict(color='#e34a33', width=2, dash='dash'),
                                  hovertemplate='%{x}: %{y:.1f} (forecast)<extra></extra>'))
    fig.update_layout(
        xaxis_title='Year', yaxis_title='CRI (0-100, higher = worse)',
        xaxis=dict(tickformat='d', dtick=1),  # a narrow year range otherwise gets fractional/comma'd ticks
        height=380, margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation='h', y=1.12), hovermode='x unified',
        yaxis_range=[0, 100],
    )
    st.plotly_chart(fig, width='stretch', key=f'{KEY}_trend_{sel_fips}', config=NO_DOWNLOAD_CONFIG)

    with st.expander('SAIDI / SAIFI history'):
        saidi_saifi = p_sel[['Year', 'SAIDI_min_per_customer', 'SAIFI_interruptions_per_customer']].dropna(
            how='all', subset=['SAIDI_min_per_customer', 'SAIFI_interruptions_per_customer'])
        if saidi_saifi.empty:
            st.caption('No SAIDI/SAIFI history available for this county.')
        else:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=saidi_saifi['Year'], y=saidi_saifi['SAIDI_min_per_customer'],
                                       name='SAIDI (min/customer)', mode='lines+markers', yaxis='y1'))
            fig2.add_trace(go.Scatter(x=saidi_saifi['Year'], y=saidi_saifi['SAIFI_interruptions_per_customer'],
                                       name='SAIFI (interruptions/customer)', mode='lines+markers', yaxis='y2'))
            fig2.update_layout(
                height=300, margin=dict(l=10, r=10, t=20, b=10),
                xaxis=dict(title='Year', tickformat='d', dtick=1),
                yaxis=dict(title='SAIDI (min/customer)'),
                yaxis2=dict(title='SAIFI', overlaying='y', side='right'),
                legend=dict(orientation='h', y=1.15),
            )
            st.plotly_chart(fig2, width='stretch', key=f'{KEY}_saidi_saifi_{sel_fips}', config=NO_DOWNLOAD_CONFIG)
            st.caption('History only -- SAIDI/SAIFI are not projected; only CRI is.')


def _render_comparison(panel, forecast, last_observed_year):
    st.subheader('Compare counties')
    latest_panel = panel.sort_values('Year').drop_duplicates('FIPS', keep='last').set_index('FIPS')
    forecast_horizon_year = last_observed_year + 3
    fc_last = forecast[forecast['Year'] == forecast_horizon_year][
        ['FIPS', 'Projected_CRI', 'Projected_Tier']
    ]

    states = sorted(panel['State'].dropna().unique())
    c1, c2, c3 = st.columns(3)
    scope = c1.radio('Scope', ['All contiguous U.S.', 'One state'], horizontal=True, key=f'{KEY}_scope')
    sort_options = {
        f'Last observed CRI ({last_observed_year}, worst first)': ('CRI', False),
        f'Last observed CRI ({last_observed_year}, best first)': ('CRI', True),
        f'{forecast_horizon_year} projected CRI (worst first)': ('Projected_CRI', False),
        f'{forecast_horizon_year} projected CRI (best first)': ('Projected_CRI', True),
    }
    sort_choice = c2.selectbox('Sort by', list(sort_options.keys()), index=2, key=f'{KEY}_sort')
    n_show = c3.slider('Counties to show', 5, 50, 15, key=f'{KEY}_n')

    la = latest_panel.reset_index().rename(columns={'Year': 'Last_Year'})
    table = la.merge(fc_last, on='FIPS', how='left')

    if scope == 'One state':
        sel_state = st.selectbox('State', states, index=states.index('MO') if 'MO' in states else 0, key=f'{KEY}_cmp_state')
        table = table[table['State'] == sel_state]

    col, asc = sort_options[sort_choice]
    table = table.sort_values(col, ascending=asc, na_position='last').head(n_show)
    table['County_Name'] = table['County_Name'].str.title()

    st.dataframe(
        table[['FIPS', 'State', 'County_Name', 'Last_Year', 'CRI', 'CRI_Tier',
               'Pct_Counties_Less_Reliable_SameYear', 'Projected_CRI', 'Projected_Tier']]
        .rename(columns={
            'Last_Year': 'Last observed year', 'CRI': 'Last observed CRI', 'CRI_Tier': 'Tier',
            'Pct_Counties_Less_Reliable_SameYear': 'More reliable than % of counties',
            'Projected_CRI': f'{forecast_horizon_year} Projected CRI', 'Projected_Tier': f'{forecast_horizon_year} Tier',
        }).round(1),
        width='stretch', hide_index=True,
    )
