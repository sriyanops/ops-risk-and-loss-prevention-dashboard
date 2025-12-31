# src/report_pdf.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, List

import pandas as pd
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
    KeepInFrame,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


@dataclass(frozen=True)
class PdfConfig:
    title: str = "Site Resource Utilization & Loss Prevention Report"
    subtitle: str = "Synthetic facility-level decision support (KPI + rules-based classification)"
    pagesize: Tuple[int, int] = letter
    margin: float = 0.65 * inch
    top_n_sites: int = 12


def _save_bar_chart(df: pd.DataFrame, x: str, y: str, title: str, out_path: Path) -> None:
    plt.figure()
    plt.bar(df[x].astype(str), df[y])
    plt.title(title)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=180)
    plt.close()


def _save_line_chart(df: pd.DataFrame, x: str, y: str, title: str, out_path: Path) -> None:
    plt.figure()
    plt.plot(df[x], df[y])
    plt.title(title)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=180)
    plt.close()


def _status_color(status: str) -> colors.Color:
    if status == "Intervention Required":
        return colors.HexColor("#B91C1C")  # red
    if status == "Watch":
        return colors.HexColor("#D97706")  # amber
    return colors.HexColor("#065F46")      # green


def _two_col_kpi_table(overall: pd.DataFrame, doc_width: float) -> Table:
    """
    Convert the wide KPI row into a vertical (Metric, Value) table
    so it never clips or overflows.
    """
    styles = getSampleStyleSheet()
    hdr = ParagraphStyle("hdr", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.white, leading=11)
    cell_l = ParagraphStyle("cell_l", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11)
    cell_r = ParagraphStyle("cell_r", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11)

    o = overall.iloc[0].to_dict()

    rows = [
        ("Planned Units", f"{int(o['planned_units']):,}"),
        ("Actual Units", f"{int(o['actual_units']):,}"),
        ("Usable Units", f"{int(o['usable_units']):,}"),
        ("Disposed Units", f"{int(o['disposed_units']):,}"),
        ("Cost Leakage", f"${float(o['cost_leakage']):,.2f}"),
        ("Avg Unit Cost", f"${float(o['avg_unit_cost']):.2f}"),
        ("Avg Loss Rate", f"{float(o['avg_loss_rate'])*100:.2f}%"),
        ("Avg Utilization", f"{float(o['avg_utilization_rate'])*100:.2f}%"),
        ("Shock Site-Days", f"{int(o['shock_days'])}"),
    ]

    data = [
        [Paragraph("Metric", hdr), Paragraph("Value", hdr)]
    ] + [
        [Paragraph(k, cell_l), Paragraph(v, cell_r)] for k, v in rows
    ]

    col_widths = [doc_width * 0.45, doc_width * 0.55]
    t = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def _site_status_table(site_status: pd.DataFrame, doc_width: float, max_rows: int = 12):
    """
    Uses Paragraph cells + width as % of doc_width so it never overflows.
    """
    cols = [
        "site_id",
        "status",
        "loss_rate_weighted",
        "cost_leakage",
        "dominant_loss_reason",
        "dominant_loss_share",
        "recommended_action",
    ]
    d = site_status[cols].head(max_rows).copy()

    # Format numeric for readability
    d["loss_rate_weighted"] = (d["loss_rate_weighted"] * 100).round(2).astype(str) + "%"
    d["dominant_loss_share"] = (d["dominant_loss_share"] * 100).round(1).astype(str) + "%"
    d["cost_leakage"] = d["cost_leakage"].round(2).map(lambda v: f"${v:,.2f}")

    styles = getSampleStyleSheet()
    hdr = ParagraphStyle(
        "hdr",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        textColor=colors.white,
        leading=10,
    )
    cell = ParagraphStyle(
        "cell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
    )

    # Shorter header labels (less wrapping pressure)
    header_labels = [
        "site id",
        "status",
        "loss rate",
        "cost leakage",
        "dominant reason",
        "dominant share",
        "recommended action",
    ]

    header_row = [Paragraph(h, hdr) for h in header_labels]

    body_rows: List[List[Paragraph]] = []
    for _, r in d.iterrows():
        body_rows.append([Paragraph(str(r[c]), cell) for c in cols])

    data = [header_row] + body_rows

    # Column widths as percentages of available document width (must sum to 1.0)
    # This guarantees the table fits inside margins and stops clipping.
    frac = [0.08, 0.14, 0.10, 0.12, 0.14, 0.10, 0.32]
    col_widths = [doc_width * f for f in frac]

    table = Table(data, repeatRows=1, colWidths=col_widths, hAlign="LEFT")
    style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ]
    )

    # Color the status cell per row (col index 1)
    for i in range(1, len(data)):
        st = d.iloc[i - 1]["status"]
        style.add("TEXTCOLOR", (1, i), (1, i), _status_color(st))
        style.add("FONTNAME", (1, i), (1, i), "Helvetica-Bold")

    table.setStyle(style)

    # Keep table inside frame; shrink only if absolutely needed
    return KeepInFrame(doc_width, 0, [table], mode="shrink")


def _table_from_df_simple(df: pd.DataFrame, doc_width: float, max_rows: int = 20) -> Table:
    """
    Generic small table: safe widths based on doc_width.
    """
    d = df.head(max_rows).copy()
    for c in d.columns:
        if pd.api.types.is_datetime64_any_dtype(d[c]):
            d[c] = d[c].dt.strftime("%Y-%m-%d")

    styles = getSampleStyleSheet()
    hdr = ParagraphStyle("hdr", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.white, leading=11)
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11)

    data = [[Paragraph(str(c), hdr) for c in d.columns]]
    for _, r in d.iterrows():
        data.append([Paragraph(str(r[c]), cell) for c in d.columns])

    n = len(d.columns)
    col_widths = [doc_width / n] * n

    t = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def build_pdf(
    output_path: str,
    overall: pd.DataFrame,
    by_site: pd.DataFrame,
    by_site_day: pd.DataFrame,
    loss_mix_by_site: pd.DataFrame,
    site_status: pd.DataFrame,
    cfg: PdfConfig = PdfConfig(),
) -> str:
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, spaceAfter=10)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#374151"))
    h_style = ParagraphStyle("H", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, spaceBefore=10, spaceAfter=6)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=cfg.pagesize,
        leftMargin=cfg.margin,
        rightMargin=cfg.margin,
        topMargin=cfg.margin,
        bottomMargin=cfg.margin,
    )
    doc_width = doc.width  # usable width inside margins (THIS is what we should fit to)

    # Charts directory
    tmp_dir = out_path.parent / "_charts_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Chart 1: Top N sites by cost leakage
    top = by_site.sort_values("cost_leakage", ascending=False).head(cfg.top_n_sites).copy()
    top["cost_leakage"] = top["cost_leakage"].round(2)
    chart1 = tmp_dir / "top_cost_leakage.png"
    _save_bar_chart(top, "site_id", "cost_leakage", "Top Sites by Cost Leakage ($)", chart1)

    # Chart 2: Daily overall cost leakage trend
    daily_overall = (
        by_site_day.groupby("date", as_index=False)
        .agg(cost_leakage=("cost_leakage", "sum"), loss_rate=("loss_rate", "mean"))
        .sort_values("date")
    )
    chart2 = tmp_dir / "overall_cost_trend.png"
    _save_line_chart(daily_overall, "date", "cost_leakage", "Overall Cost Leakage Trend ($/day)", chart2)

    story = []
    story.append(Paragraph(cfg.title, title_style))
    story.append(Paragraph(cfg.subtitle, sub_style))
    story.append(Spacer(1, 0.15 * inch))

    # Executive summary
    story.append(Paragraph("Executive Summary", h_style))
    o = overall.iloc[0].to_dict()
    exec_text = (
        f"Across the analysis window, the system processed <b>{int(o['actual_units']):,}</b> actual units "
        f"and identified <b>{int(o['disposed_units']):,}</b> disposed units, with total estimated cost leakage of "
        f"<b>${float(o['cost_leakage']):,.2f}</b>. Average utilization was <b>{float(o['avg_utilization_rate'])*100:.2f}%</b> "
        f"and average loss rate was <b>{float(o['avg_loss_rate'])*100:.2f}%</b>. "
        f"Operational shock flags were present on <b>{int(o['shock_days'])}</b> site-days."
    )
    story.append(Paragraph(exec_text, styles["BodyText"]))
    story.append(Spacer(1, 0.15 * inch))

    # Overall KPIs (vertical table — no clipping possible)
    story.append(Paragraph("Overall KPIs", h_style))
    story.append(_two_col_kpi_table(overall, doc_width))
    story.append(Spacer(1, 0.2 * inch))

    # Site status table (width-safe)
    story.append(Paragraph("Site Risk & Recommended Actions (Top)", h_style))
    story.append(_site_status_table(site_status, doc_width, max_rows=cfg.top_n_sites))
    story.append(Spacer(1, 0.2 * inch))

    # Charts page
    story.append(PageBreak())
    story.append(Paragraph("Key Visuals", h_style))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("Top Sites by Cost Leakage", styles["BodyText"]))
    story.append(Image(str(chart1), width=doc_width, height=3.8 * inch))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Overall Cost Leakage Trend", styles["BodyText"]))
    story.append(Image(str(chart2), width=doc_width, height=3.8 * inch))
    story.append(Spacer(1, 0.2 * inch))

    # Loss driver mix summary (overall)
    story.append(Paragraph("Loss Driver Mix (Overall)", h_style))
    mix_overall = (
        loss_mix_by_site.groupby("loss_reason", as_index=False)
        .agg(disposed_units=("disposed_units", "sum"))
        .sort_values("disposed_units", ascending=False)
    )
    total = mix_overall["disposed_units"].sum()
    mix_overall["disposed_share"] = (mix_overall["disposed_units"] / total).round(4)
    mix_overall["disposed_share"] = mix_overall["disposed_share"].map(lambda v: f"{float(v)*100:.1f}%")

    story.append(_table_from_df_simple(mix_overall, doc_width, max_rows=10))

    doc.build(story)
    return str(out_path)

