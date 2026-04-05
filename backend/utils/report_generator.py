import csv
import io
import time
import logging
from typing import Any

logger = logging.getLogger(__name__)
try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, HRFlowable,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not installed — PDF export disabled")


FLOW_COLUMNS = [
    "id", "timestamp", "src_ip", "dst_ip", "src_port", "dst_port",
    "protocol", "duration", "packet_count", "byte_count", "avg_pkt_size",
    "flow_label", "app_fingerprint", "anomaly_score", "is_anomaly",
    "anomaly_type", "threat_score", "src_country", "src_city",
]

ALERT_COLUMNS = [
    "id", "timestamp", "alert_type", "severity", "src_ip", "dst_ip", "message",
]


def generate_csv(flows: list[dict], alerts: list[dict]) -> bytes:
    """
    Generate a ZIP-like CSV report with flows and alerts as separate sections.
    Returns bytes ready for HTTP response.
    """
    output = io.StringIO()

    output.write("# FLOWS\n")
    writer = csv.DictWriter(output, fieldnames=FLOW_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for flow in flows:
        row = dict(flow)
        row["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(flow.get("timestamp", 0)))
        row["is_anomaly"] = "Yes" if flow.get("is_anomaly") else "No"
        writer.writerow(row)

    output.write("\n# ALERTS\n")
    alert_writer = csv.DictWriter(output, fieldnames=ALERT_COLUMNS, extrasaction="ignore")
    alert_writer.writeheader()
    for alert in alerts:
        row = dict(alert)
        row["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(alert.get("timestamp", 0)))
        alert_writer.writerow(row)

    return output.getvalue().encode("utf-8")


def generate_pdf(
    flows: list[dict],
    alerts: list[dict],
    stats: dict,
    session_id: str = "",
) -> bytes:
    """
    Generate a professional PDF report.
    Returns bytes ready for HTTP response.
    """
    if not REPORTLAB_AVAILABLE:
        return _pdf_fallback(flows, alerts, stats)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=1 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontSize=22,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#444"),
        spaceAfter=20,
    )

    elements.append(Paragraph("Traffic Classification Report", title_style))
    elements.append(Paragraph(
        f"Session: {session_id or 'N/A'} | Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        subtitle_style,
    ))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#333")))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Session Summary", styles["Heading2"]))
    elements.append(Spacer(1, 6))

    stat_data = [
        ["Metric", "Value"],
        ["Total Flows", str(stats.get("total_flows", 0))],
        ["Total Packets", str(stats.get("total_packets", 0))],
        ["Total Bytes", _fmt_bytes(stats.get("total_bytes", 0))],
        ["Anomalies Detected", str(stats.get("anomaly_count", 0))],
        ["Avg Threat Score", f"{stats.get('avg_threat', 0):.1f}/100"],
        ["Alerts Generated", str(len(alerts))],
    ]

    stat_table = Table(stat_data, colWidths=[3 * inch, 3 * inch])
    stat_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#ccc")),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(stat_table)
    elements.append(Spacer(1, 20))

    if alerts:
        elements.append(Paragraph("Security Alerts", styles["Heading2"]))
        elements.append(Spacer(1, 6))

        alert_headers = ["Time", "Type", "Severity", "Source IP", "Message"]
        alert_rows = [alert_headers]
        for a in alerts[:50]:
            alert_rows.append([
                time.strftime("%H:%M:%S", time.localtime(a.get("timestamp", 0))),
                a.get("alert_type", ""),
                a.get("severity", "").upper(),
                a.get("src_ip", ""),
                a.get("message", "")[:60] + "..." if len(a.get("message", "")) > 60 else a.get("message", ""),
            ])

        alert_table = Table(alert_rows, colWidths=[0.8*inch, 1.2*inch, 0.8*inch, 1.2*inch, 3*inch])
        _apply_severity_styles(alert_table, alert_rows)
        elements.append(alert_table)
        elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"Flow Records (Top {min(100, len(flows))})", styles["Heading2"]))
    elements.append(Spacer(1, 6))

    flow_headers = ["Time", "Src IP", "Dst IP", "Proto", "Bytes", "Label", "Threat"]
    flow_rows = [flow_headers]
    for f in flows[:100]:
        flow_rows.append([
            time.strftime("%H:%M:%S", time.localtime(f.get("timestamp", 0))),
            f.get("src_ip", ""),
            f.get("dst_ip", ""),
            f.get("protocol", ""),
            _fmt_bytes(f.get("byte_count", 0)),
            f.get("flow_label", "Unknown"),
            str(f.get("threat_score", 0)),
        ])

    flow_table = Table(
        flow_rows,
        colWidths=[0.8*inch, 1.2*inch, 1.2*inch, 0.6*inch, 0.8*inch, 1.2*inch, 0.6*inch],
    )
    flow_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#ddd")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(flow_table)

    doc.build(elements)
    return buffer.getvalue()


def _apply_severity_styles(table, rows):
    """Color-code alert rows by severity."""
    severity_colors = {
        "CRITICAL": colors.HexColor("#ff4444"),
        "HIGH": colors.HexColor("#ff8800"),
        "MEDIUM": colors.HexColor("#ffcc00"),
        "LOW": colors.HexColor("#88cc00"),
    }
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#ddd")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]
    for i, row in enumerate(rows[1:], 1):
        sev = row[2] if len(row) > 2 else ""
        if sev in severity_colors:
            style.append(("BACKGROUND", (2, i), (2, i), severity_colors[sev]))
            style.append(("TEXTCOLOR", (2, i), (2, i), colors.white))
    table.setStyle(TableStyle(style))


def _fmt_bytes(b: int) -> str:
    """Human-readable byte count."""
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def _pdf_fallback(flows, alerts, stats) -> bytes:
    """Simple text-based PDF fallback if reportlab not installed."""
    lines = [
        "Traffic Classification Report",
        "=" * 50,
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "Summary:",
        f"  Total Flows: {stats.get('total_flows', 0)}",
        f"  Anomalies: {stats.get('anomaly_count', 0)}",
        f"  Alerts: {len(alerts)}",
        "",
        "Install 'reportlab' for proper PDF generation:",
        "  pip install reportlab",
    ]
    return "\n".join(lines).encode("utf-8")
