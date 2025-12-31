# src/rules.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd


Status = Literal["Normal", "Watch", "Intervention Required"]


@dataclass(frozen=True)
class RuleConfig:
    # Thresholds for site-level evaluation (weighted loss rate)
    normal_max_loss: float = 0.05
    watch_max_loss: float = 0.10

    # Persistence rules
    sustained_watch_loss: float = 0.08
    sustained_days: int = 5

    # Dominant driver rule
    dominant_driver_share: float = 0.60

    # Trend rule (cost leakage rising)
    trend_days: int = 3


ACTION_MAP = {
    "overproduction": "Adjust ordering cadence / tighten plan vs actual variance; review reorder points.",
    "spoilage": "Strengthen process controls (handling/storage); investigate temperature excursions and SOP adherence.",
    "damage": "Improve handling/packaging; target training and standard work to reduce breakage.",
    "timing_mismatch": "Fix scheduling + staffing alignment; coordinate inbound timing and process capacity.",
}


def _rising_streak(values: pd.Series, k: int) -> bool:
    """True if last k values are strictly increasing."""
    if len(values) < k:
        return False
    tail = values.tail(k).tolist()
    return all(tail[i] < tail[i + 1] for i in range(len(tail) - 1))


def classify_sites(
    by_site: pd.DataFrame,
    by_site_day: pd.DataFrame,
    loss_mix_by_site: pd.DataFrame,
    cfg: RuleConfig = RuleConfig(),
) -> pd.DataFrame:
    """
    Inputs come from src.kpis.compute_kpis():
      - by_site: aggregated per site
      - by_site_day: daily per site (for trend/persistence)
      - loss_mix_by_site: driver mix per site

    Output: site-level status + key drivers + recommended action.
    """
    # Guardrails
    required_site_cols = {"site_id", "cost_leakage", "loss_rate_weighted"}
    if not required_site_cols.issubset(by_site.columns):
        raise ValueError(f"by_site missing columns: {sorted(required_site_cols - set(by_site.columns))}")

    # Determine dominant driver per site
    dom = (
        loss_mix_by_site.sort_values(["site_id", "disposed_share"], ascending=[True, False])
        .groupby("site_id", as_index=False)
        .first()[["site_id", "loss_reason", "disposed_share"]]
        .rename(columns={"loss_reason": "dominant_loss_reason", "disposed_share": "dominant_loss_share"})
    )

    out = by_site.merge(dom, on="site_id", how="left")

    # Compute persistence: count last N days where loss_rate >= sustained_watch_loss
    def sustained_flag(site_id: str) -> bool:
        d = by_site_day[by_site_day["site_id"] == site_id].sort_values("date")
        tail = d.tail(cfg.sustained_days)
        if len(tail) < cfg.sustained_days:
            return False
        return bool((tail["loss_rate"] >= cfg.sustained_watch_loss).all())

    # Compute trend: cost leakage rising for last N days
    def rising_cost_flag(site_id: str) -> bool:
        d = by_site_day[by_site_day["site_id"] == site_id].sort_values("date")
        return _rising_streak(d["cost_leakage"], cfg.trend_days)

    sustained = []
    rising = []
    for sid in out["site_id"].tolist():
        sustained.append(int(sustained_flag(sid)))
        rising.append(int(rising_cost_flag(sid)))

    out["sustained_high_loss_flag"] = sustained
    out["rising_cost_leakage_flag"] = rising

    # Status logic
    statuses: list[Status] = []
    for _, r in out.iterrows():
        lr = float(r["loss_rate_weighted"])
        dom_share = float(r["dominant_loss_share"]) if pd.notna(r["dominant_loss_share"]) else 0.0
        sustained_flag_i = int(r["sustained_high_loss_flag"]) == 1
        rising_flag_i = int(r["rising_cost_leakage_flag"]) == 1

        if lr > cfg.watch_max_loss or sustained_flag_i or (dom_share >= cfg.dominant_driver_share and lr > cfg.normal_max_loss):
            statuses.append("Intervention Required")
        elif lr > cfg.normal_max_loss or rising_flag_i:
            statuses.append("Watch")
        else:
            statuses.append("Normal")

    out["status"] = statuses

    # Recommended action based on dominant driver
    def recommend(reason: str) -> str:
        if pd.isna(reason):
            return "Review site performance; insufficient driver data."
        return ACTION_MAP.get(str(reason), "Review site performance; define corrective action.")

    out["recommended_action"] = out["dominant_loss_reason"].apply(recommend)

    # Formatting
    out["dominant_loss_share"] = out["dominant_loss_share"].fillna(0.0).round(4)
    out["loss_rate_weighted"] = out["loss_rate_weighted"].round(4)
    out["cost_leakage"] = out["cost_leakage"].round(2)

    cols = [
        "site_id",
        "status",
        "loss_rate_weighted",
        "cost_leakage",
        "shock_days",
        "dominant_loss_reason",
        "dominant_loss_share",
        "sustained_high_loss_flag",
        "rising_cost_leakage_flag",
        "recommended_action",
    ]
    # Keep only columns that exist (shock_days should exist from kpis output)
    cols = [c for c in cols if c in out.columns]
    return out[cols].sort_values(["status", "cost_leakage"], ascending=[True, False]).reset_index(drop=True)
