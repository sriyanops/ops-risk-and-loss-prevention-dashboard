# src/app.py
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.io import load_daily_data
from src.kpis import compute_kpis
from src.rules import classify_sites
from src.report_pdf import build_pdf
from src.config import REPORT_PATH

st.set_page_config(page_title="Site Resource Ops Tool", layout="wide")


@st.cache_data
def load_raw() -> pd.DataFrame:
    """
    Loads the daily dataset using src.io (schema-validated).
    Uses OPS_DATA_DIR env var via config.py to select data/raw vs data/sample.
    """
    df = load_daily_data()
    # io.py already parses date; this is harmless redundancy but keeps behavior stable
    df["date"] = pd.to_datetime(df["date"])
    return df


def _status_chip(status: str) -> str:
    # Emoji chips (reliable across Streamlit themes)
    if status == "Intervention Required":
        return "🔴 Intervention Required"
    if status == "Watch":
        return "🟠 Watch"
    return "🟢 Normal"


def _prettify_reason(reason: str) -> str:
    # timing_mismatch -> Timing mismatch
    return str(reason).replace("_", " ").strip().title()


def _ensure_pdf(
    overall: pd.DataFrame,
    by_site: pd.DataFrame,
    by_site_day: pd.DataFrame,
    loss_mix_by_site: pd.DataFrame,
    site_status: pd.DataFrame,
) -> Path:
    """
    Ensures the executive PDF exists (all-data report).
    Writes to REPORT_PATH (repo root /reports/...).
    """
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Generate once for consistency (do not regenerate per filter state)
    if not REPORT_PATH.exists():
        build_pdf(
            output_path=str(REPORT_PATH),
            overall=overall,
            by_site=by_site,
            by_site_day=by_site_day,
            loss_mix_by_site=loss_mix_by_site,
            site_status=site_status,
        )
    return REPORT_PATH


def main():
    root = Path(__file__).resolve().parents[1]

    st.title("Site Resource Utilization & Loss Prevention")
    st.caption("KPI computation + rules-based site classification (synthetic dataset)")

    df = load_raw()

    # ---------- Sidebar controls ----------
    st.sidebar.header("Filters")

    site_ids = sorted(df["site_id"].unique().tolist())
    selected_sites = st.sidebar.multiselect("Sites", site_ids, default=site_ids)

    date_min = df["date"].min().date()
    date_max = df["date"].max().date()
    start_date, end_date = st.sidebar.date_input("Date range", (date_min, date_max))

    # Drilldown selector
    st.sidebar.header("Drilldown")
    drill_site = st.sidebar.selectbox("Inspect a single site", ["(none)"] + site_ids, index=0)

    # ---------- Filtered dataset ----------
    dff = df[
        (df["site_id"].isin(selected_sites))
        & (df["date"].dt.date >= start_date)
        & (df["date"].dt.date <= end_date)
    ].copy()

    # Compute KPIs on filtered set
    kpi_f = compute_kpis(dff)
    status_f = classify_sites(kpi_f.by_site, kpi_f.by_site_day, kpi_f.loss_mix_by_site)

    # ---------- Top KPI tiles ----------
    o = kpi_f.overall.iloc[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Actual Units", f"{int(o['actual_units']):,}")
    c2.metric("Disposed Units", f"{int(o['disposed_units']):,}")
    c3.metric("Cost Leakage", f"${float(o['cost_leakage']):,.2f}")
    c4.metric("Avg Loss Rate", f"{float(o['avg_loss_rate'])*100:.2f}%")
    c5.metric("Avg Utilization", f"{float(o['avg_utilization_rate'])*100:.2f}%")

    # ---------- PDF download (ALL DATA) ----------
    # Generate a consistent executive PDF (all data, not filtered)
    kpi_all = compute_kpis(df)
    status_all = classify_sites(kpi_all.by_site, kpi_all.by_site_day, kpi_all.loss_mix_by_site)
    pdf_path = _ensure_pdf(
        kpi_all.overall,
        kpi_all.by_site,
        kpi_all.by_site_day,
        kpi_all.loss_mix_by_site,
        status_all,
    )

    with open(pdf_path, "rb") as f:
        st.download_button(
            label="Download Executive PDF Report",
            data=f,
            file_name=pdf_path.name,
            mime="application/pdf",
        )

    st.divider()

    # ---------- Status table + Top leakage ----------
    left, right = st.columns([1.45, 1.0])

    with left:
        st.subheader("Site Risk & Recommended Actions")

        # Add visual chips + nicer reason labels
        show = status_f.copy()
        show["status"] = show["status"].apply(_status_chip)
        if "dominant_loss_reason" in show.columns:
            show["dominant_loss_reason"] = show["dominant_loss_reason"].apply(_prettify_reason)

        st.dataframe(show, use_container_width=True, hide_index=True)

    with right:
        st.subheader("Top Sites by Cost Leakage")
        top = kpi_f.by_site.sort_values("cost_leakage", ascending=False).head(10)[["site_id", "cost_leakage"]]
        st.bar_chart(top.set_index("site_id")["cost_leakage"])

    st.divider()

    # ---------- Trends (filtered) ----------
    st.subheader("Trends (Filtered)")

    trend = (
        kpi_f.by_site_day.groupby("date", as_index=False)
        .agg(cost_leakage=("cost_leakage", "sum"), loss_rate=("loss_rate", "mean"))
        .sort_values("date")
    )

    t1, t2 = st.columns(2)
    with t1:
        st.caption("Cost Leakage ($/day)")
        st.line_chart(trend.set_index("date")["cost_leakage"])
    with t2:
        st.caption("Avg Loss Rate")
        st.line_chart(trend.set_index("date")["loss_rate"])

    st.divider()

    # ---------- Driver mix (filtered) ----------
    st.subheader("Loss Driver Mix (Filtered)")
    mix = (
        kpi_f.loss_mix_by_site.groupby("loss_reason", as_index=False)
        .agg(disposed_units=("disposed_units", "sum"))
        .sort_values("disposed_units", ascending=False)
    )
    mix["loss_reason"] = mix["loss_reason"].apply(_prettify_reason)
    st.bar_chart(mix.set_index("loss_reason")["disposed_units"])

    # ---------- Site drilldown ----------
    if drill_site != "(none)":
        st.divider()
        st.subheader(f"Site Drilldown: {drill_site}")

        site_df = df[df["site_id"] == drill_site].copy()
        # Daily trend for the site
        site_day = compute_kpis(site_df).by_site_day.sort_values("date")

        d1, d2 = st.columns(2)
        with d1:
            st.caption("Site Cost Leakage ($/day)")
            s_trend = (
                site_day.groupby("date", as_index=False)
                .agg(cost_leakage=("cost_leakage", "sum"))
                .sort_values("date")
            )
            st.line_chart(s_trend.set_index("date")["cost_leakage"])

        with d2:
            st.caption("Site Loss Rate")
            s_trend2 = (
                site_day.groupby("date", as_index=False)
                .agg(loss_rate=("loss_rate", "mean"))
                .sort_values("date")
            )
            st.line_chart(s_trend2.set_index("date")["loss_rate"])

        # Driver mix for the site
        st.caption("Site Loss Driver Mix")
        site_mix = (
            compute_kpis(site_df).loss_mix_by_site.groupby("loss_reason", as_index=False)
            .agg(disposed_units=("disposed_units", "sum"))
            .sort_values("disposed_units", ascending=False)
        )
        site_mix["loss_reason"] = site_mix["loss_reason"].apply(_prettify_reason)
        st.bar_chart(site_mix.set_index("loss_reason")["disposed_units"])

        # Show the site status row (from all-data classification)
        st.caption("Site Classification (All Data)")
        srow = status_all[status_all["site_id"] == drill_site].copy()
        if not srow.empty:
            srow_disp = srow.copy()
            srow_disp["status"] = srow_disp["status"].apply(_status_chip)
            if "dominant_loss_reason" in srow_disp.columns:
                srow_disp["dominant_loss_reason"] = srow_disp["dominant_loss_reason"].apply(_prettify_reason)
            st.dataframe(srow_disp, use_container_width=True, hide_index=True)

    st.caption("Note: KPIs/status recompute on the filtered subset. PDF download is the all-data executive report.")


if __name__ == "__main__":
    main()

