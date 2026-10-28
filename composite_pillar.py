"""Composite Power Risk Index: not yet built. Honest placeholder -- no
synthetic or invented combined score is ever shown here."""
import streamlit as st


def render():
    st.subheader("Composite Power Risk Index")
    st.warning(
        "**Not yet available.** Combining the Cost, Reliability, and "
        "Availability pillars into a single index requires deciding a "
        "normalization and weighting methodology across pillars that are "
        "measured in completely different units (cents/kWh, a constructed "
        "0-100 reliability index, and whatever the Availability pillar "
        "produces) -- a methodology decision, not just an engineering one, "
        "still to be made. No invented combined score is shown here in the "
        "meantime."
    )
    st.markdown(
        "This page will be built once all three pillars have real, validated "
        "results and a defensible combination methodology has been agreed on."
    )
