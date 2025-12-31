# src/kpis.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

KpiLevel = Literal["overall", "site", "site_day", "site_reason"]


@dataclass(frozen=True)
class KpiOutputs:
    overall: pd.DataFrame
    by_site: pd.DataFrame
    by_site_day: pd.DataFrame
    loss_mix_by_site: pd.DataFrame


# These are required for your KPI logic (and mirror what your dataset already includes).
REQUIRED_COLS = {
    "date",
    "site_id",
    "planned_units",
    "actual_units",
    "usable_units",
    "disposed_units",
    "unit_cost",
    "loss_reason",
    "staffing_shortfall_flag",
    "supplier_delay_flag",
    "temp_excursion_flag",
}


def _validate_schema(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}. Found: {list(df.columns)}"
        )


def _normalize_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize types for downstream KPI computations.
    This does NOT read files; it assumes df is already loaded.
    """
    out = df.copy()

    # Parse date
    out["date"] = pd.to_datetime(out["date"], errors="raise")

    # Numeric fields
    for c in ("planned_units", "actual_units", "usable_units", "disposed_units"):
        out[c] = pd.to_numeric(out[c], errors="raise").astype(int)

    out["unit_cost"] = pd.to_numeric(out["unit_cost"], errors="raise").astype(float)

    # Flags (0/1)
    for c in ("staffing_shortfall_flag", "supplier_delay_flag", "temp_excursion_flag"):
        out[c] = pd.to_numeric(out[c], errors="raise").astype(int)

    # Integrity check: usable + disposed must equal actual
    bad = out["usable_units"] + out["disposed_units"] != out["actual_units"]
    if bad.any():
        n = int(bad.sum())
        raise ValueError(
            f"Integrity check failed: usable+disposed != actual for {n} rows."
        )

    return out


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # Avoid divide-by-zero issues by using where actual_units > 0
    out["utilization_rate"] = (
        (out["usable_units"] / out["actual_units"])
        .where(out["actual_units"] > 0, 0.0)
    )
    out["loss_rate"] = (
        (out["disposed_units"] / out["actual_units"])
        .where(out["actual_units"] > 0, 0.0)
    )

    out["cost_leakage"] = out["disposed_units"] * out["unit_cost"]
    out["plan_variance_units"] = out["actual_units"] - out["planned_units"]

    # Helpful rollup flags
    out["any_shock_flag"] = (
        (out["staffing_shortfall_flag"] == 1)
        | (out["supplier_delay_flag"] == 1)
        | (out["temp_excursion_flag"] == 1)
    ).astype(int)

    return out


def compute_kpis(df: pd.DataFrame) -> KpiOutputs:
    """
    Compute KPI tables from an already-loaded daily fact DataFrame.
    """
    _validate_schema(df)
    d0 = _normalize_types(df)
    d = add_derived_metrics(d0)

    # Overall rollup
    overall = pd.DataFrame(
        {
            "planned_units": [d["planned_units"].sum()],
            "actual_units": [d["actual_units"].sum()],
            "usable_units": [d["usable_units"].sum()],
            "disposed_units": [d["disposed_units"].sum()],
            "cost_leakage": [round(d["cost_leakage"].sum(), 2)],
            "avg_unit_cost": [round(d["unit_cost"].mean(), 2)],
            "avg_loss_rate": [round(d["loss_rate"].mean(), 4)],
            "avg_utilization_rate": [round(d["utilization_rate"].mean(), 4)],
            "shock_days": [int(d["any_shock_flag"].sum())],
        }
    )

    # By-site rollup
    by_site = (
        d.groupby("site_id", as_index=False)
        .agg(
            planned_units=("planned_units", "sum"),
            actual_units=("actual_units", "sum"),
            usable_units=("usable_units", "sum"),
            disposed_units=("disposed_units", "sum"),
            cost_leakage=("cost_leakage", "sum"),
            avg_unit_cost=("unit_cost", "mean"),
            avg_loss_rate=("loss_rate", "mean"),
            avg_utilization_rate=("utilization_rate", "mean"),
            shock_days=("any_shock_flag", "sum"),
        )
    )

    # Add ratio metrics at aggregated level (more meaningful than averaging ratios)
    by_site["loss_rate_weighted"] = (
        (by_site["disposed_units"] / by_site["actual_units"])
        .where(by_site["actual_units"] > 0, 0.0)
    )
    by_site["utilization_rate_weighted"] = (
        (by_site["usable_units"] / by_site["actual_units"])
        .where(by_site["actual_units"] > 0, 0.0)
    )

    # Rounding for cleanliness
    by_site["cost_leakage"] = by_site["cost_leakage"].round(2)
    by_site["avg_unit_cost"] = by_site["avg_unit_cost"].round(2)
    for c in ("avg_loss_rate", "avg_utilization_rate", "loss_rate_weighted", "utilization_rate_weighted"):
        by_site[c] = by_site[c].round(4)

    # By-site-day (for trends)
    by_site_day = (
        d.groupby(["date", "site_id"], as_index=False)
        .agg(
            planned_units=("planned_units", "sum"),
            actual_units=("actual_units", "sum"),
            usable_units=("usable_units", "sum"),
            disposed_units=("disposed_units", "sum"),
            cost_leakage=("cost_leakage", "sum"),
            any_shock_flag=("any_shock_flag", "max"),
        )
    )

    by_site_day["loss_rate"] = (
        (by_site_day["disposed_units"] / by_site_day["actual_units"])
        .where(by_site_day["actual_units"] > 0, 0.0)
    ).round(4)
    by_site_day["utilization_rate"] = (
        (by_site_day["usable_units"] / by_site_day["actual_units"])
        .where(by_site_day["actual_units"] > 0, 0.0)
    ).round(4)
    by_site_day["cost_leakage"] = by_site_day["cost_leakage"].round(2)

    # Loss mix by site (driver breakdown)
    mix = (
        d.groupby(["site_id", "loss_reason"], as_index=False)
        .agg(disposed_units=("disposed_units", "sum"))
    )
    total_disposed = mix.groupby("site_id", as_index=False).agg(total_disposed=("disposed_units", "sum"))
    loss_mix_by_site = mix.merge(total_disposed, on="site_id", how="left")
    loss_mix_by_site["disposed_share"] = (
        (loss_mix_by_site["disposed_units"] / loss_mix_by_site["total_disposed"])
        .where(loss_mix_by_site["total_disposed"] > 0, 0.0)
        .round(4)
    )

    return KpiOutputs(
        overall=overall,
        by_site=by_site.sort_values("cost_leakage", ascending=False).reset_index(drop=True),
        by_site_day=by_site_day.sort_values(["site_id", "date"]).reset_index(drop=True),
        loss_mix_by_site=loss_mix_by_site.sort_values(
            ["site_id", "disposed_share"],
            ascending=[True, False],
        ).reset_index(drop=True),
    )
