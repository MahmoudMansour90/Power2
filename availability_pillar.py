"""Availability / Capacity pillar: not yet built. Honest placeholder --
no synthetic or placeholder numbers are ever shown here."""
import streamlit as st


def render():
    st.subheader("Availability / Capacity pillar")
    st.warning(
        "**Not yet available.** This pillar is still being scoped and does not "
        "yet have a validated historical panel or forecast -- so nothing is "
        "shown here rather than a placeholder or synthetic number."
    )
    st.markdown(
        "What's known so far about this pillar's data constraints:\n\n"
        "- The peak-demand dimension is built on EIA Form 930 hourly "
        "balancing-authority data, reliably available only from around 2018 "
        "onward -- a shorter history than Cost or Reliability.\n"
        "- The transmission connectivity score dimension appears to be a "
        "static/snapshot infrastructure metric with no natural year-to-year "
        "history to forecast from.\n\n"
        "This page will be filled in once a validated panel and (if feasible) "
        "a forecast exist for this pillar, following the same real-data, "
        "tested-before-shipped discipline as the Cost and Reliability pages."
    )
