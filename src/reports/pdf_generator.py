"""Generate PDF reports"""

from src.time_utils import get_local_time
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)


# Brand colors
PURPLE = colors.HexColor("#a855f7")
DARK_PURPLE = colors.HexColor("#7e22ce")
BLACK = colors.HexColor("#000000")
WHITE = colors.HexColor("#ffffff")
GRAY = colors.HexColor("#6b7280")


def generate_report(
    run_id: str,
    summary: dict,
    comparisons: list,
    charts_dir: str,
    output_path: str,
    report_type: str = "technical",
):
    """Generate PDF report for a benchmark run"""

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "Title_Custom",
        parent=styles["Title"],
        fontSize=24,
        textColor=PURPLE,
        spaceAfter=30,
    ))

    styles.add(ParagraphStyle(
        "Heading_Custom",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=DARK_PURPLE,
        spaceBefore=20,
        spaceAfter=10,
    ))

    styles.add(ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontSize=10,
        textColor=BLACK,
        spaceAfter=8,
    ))

    elements = []

    # Title page
    elements.append(Spacer(1, 2 * inch))
    elements.append(Paragraph(
        "Benchmark AI Server System Report",
        styles["Title_Custom"],
    ))
    elements.append(Paragraph(
        f"Run ID: {run_id}",
        styles["Body_Custom"],
    ))
    elements.append(Paragraph(
        f"Generated: {get_local_time().strftime('%Y-%m-%d %H:%M UTC')}",
        styles["Body_Custom"],
    ))

    if report_type == "executive":
        elements.append(Paragraph(
            "Executive Summary",
            styles["Body_Custom"],
        ))

    elements.append(PageBreak())

    # Summary section
    elements.append(Paragraph(
        "Performance Summary",
        styles["Heading_Custom"],
    ))

    s1 = summary.get("server1", {})
    s2 = summary.get("server2", {})

    table_data = [
        ["Metric", "Server 1 (Native)", "Server 2 (Optimized)", "Delta"],
    ]

    metric_pairs = [
        ("TTFT (ms)", "avg_ttft_ms", True),
        ("TPOT (ms)", "avg_tpot_ms", True),
        ("TPS", "avg_tps", False),
        ("RPS", "avg_rps", False),
        ("P99 Latency (ms)", "avg_p99_ms", True),
    ]

    for label, key, lower_is_better in metric_pairs:
        v1 = s1.get(key)
        v2 = s2.get(key)
        v1_str = f"{v1:.2f}" if v1 else "--"
        v2_str = f"{v2:.2f}" if v2 else "--"

        delta_str = "--"
        if v1 and v2 and v1 != 0:
            delta = ((v2 - v1) / abs(v1)) * 100
            if lower_is_better:
                delta = -delta
            sign = "+" if delta > 0 else ""
            delta_str = f"{sign}{delta:.1f}%"

        table_data.append([label, v1_str, v2_str, delta_str])

    table = Table(table_data, colWidths=[120, 110, 130, 80])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PURPLE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#f3e8ff")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # Charts
    charts_path = Path(charts_dir)
    for chart_file in sorted(charts_path.glob("*.png")):
        elements.append(Paragraph(
            chart_file.stem.replace("_", " ").title(),
            styles["Heading_Custom"],
        ))
        elements.append(Image(
            str(chart_file),
            width=6 * inch,
            height=3.5 * inch,
        ))
        elements.append(Spacer(1, 10))

    doc.build(elements)