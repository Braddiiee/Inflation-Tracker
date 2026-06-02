"""
PDF inflation report generation.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.data_processor import compute_dashboard_metrics, load_analytics_dataframe


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Heading1"],
            fontSize=18,
            spaceAfter=12,
        ),
        "heading": ParagraphStyle(
            "ReportHeading",
            parent=base["Heading2"],
            fontSize=13,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": base["Normal"],
    }


def generate_pdf_report_bytes(*, db_path=None) -> bytes:
    """
    Build a PDF summary: KPIs, monthly inflation table, recent records.

    Returns raw PDF bytes suitable for st.download_button.
    """
    df = load_analytics_dataframe(db_path=db_path)
    metrics = compute_dashboard_metrics(df)
    styles = _styles()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    story: list = []

    story.append(Paragraph("Grocery Inflation Tracker — Report", styles["title"]))
    story.append(
        Paragraph(
            f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            styles["body"],
        )
    )
    story.append(Spacer(1, 12))

    # KPI table
    story.append(Paragraph("Summary", styles["heading"]))
    kpi_data = [
        ["Metric", "Value"],
        [
            "Current basket cost",
            f"{metrics.current_basket_cost:,.2f}"
            if metrics.current_basket_cost is not None
            else "—",
        ],
        [
            "Weekly change",
            f"{metrics.weekly_change.percent_change:+.2f}%"
            if metrics.weekly_change.percent_change is not None
            else "—",
        ],
        [
            "Monthly change",
            f"{metrics.monthly_change.percent_change:+.2f}%"
            if metrics.monthly_change.percent_change is not None
            else "—",
        ],
        [
            "Highest inflation item",
            f"{metrics.highest_inflation_item.item_name} ({metrics.highest_inflation_item.percentage_change:+.1f}%)"
            if metrics.highest_inflation_item
            else "—",
        ],
        [
            "Lowest inflation item",
            f"{metrics.lowest_inflation_item.item_name} ({metrics.lowest_inflation_item.percentage_change:+.1f}%)"
            if metrics.lowest_inflation_item
            else "—",
        ],
        ["Observations", str(metrics.observation_count)],
        ["Items tracked", str(metrics.item_count)],
    ]
    kpi_table = Table(kpi_data, colWidths=[2.8 * inch, 3.2 * inch])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # Monthly inflation
    if metrics.monthly_inflation:
        story.append(Paragraph("Monthly inflation", styles["heading"]))
        inf_rows = [["Month", "Basket cost", "MoM %"]]
        for row in metrics.monthly_inflation:
            inf_rows.append(
                [
                    row.month,
                    f"{row.basket_cost:,.2f}",
                    f"{row.inflation_pct:+.2f}%" if row.inflation_pct is not None else "—",
                ]
            )
        inf_table = Table(inf_rows, colWidths=[1.8 * inch, 1.8 * inch, 1.4 * inch])
        inf_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#64748b")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )
        story.append(inf_table)
        story.append(Spacer(1, 14))

    # Recent records (up to 25)
    story.append(Paragraph("Recent price entries", styles["heading"]))
    if df.empty:
        story.append(Paragraph("No records in database.", styles["body"]))
    else:
        recent = df.sort_values(["date_recorded", "log_id"], ascending=False).head(25)
        recent = recent.copy()
        recent["date_recorded"] = pd.to_datetime(recent["date_recorded"]).dt.strftime(
            "%Y-%m-%d"
        )
        table_data = [
            ["Date", "Item", "Store", "Price", "Unit price"],
        ]
        for _, r in recent.iterrows():
            table_data.append(
                [
                    r["date_recorded"],
                    str(r["item_name"])[:24],
                    str(r["store_name"])[:18],
                    f"{r['price_total']:.2f}",
                    f"{r['unit_price']:.2f}",
                ]
            )
        rec_table = Table(
            table_data,
            colWidths=[0.9 * inch, 1.6 * inch, 1.3 * inch, 0.8 * inch, 0.9 * inch],
        )
        rec_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ]
            )
        )
        story.append(rec_table)

    doc.build(story)
    return buffer.getvalue()


def default_pdf_filename() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"inflation_report_{stamp}.pdf"
