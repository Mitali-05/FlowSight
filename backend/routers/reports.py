import time
from fastapi import APIRouter, Query
from fastapi.responses import Response

from database import get_db, get_flows, get_stats
from utils.report_generator import generate_csv, generate_pdf

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/csv")
async def export_csv(session_id: str | None = None, limit: int = Query(5000, le=50000)):
    """Export flows and alerts as CSV."""
    db = await get_db()
    try:
        flows = await get_flows(db, limit=limit, session_id=session_id)
        alert_rows = await db.execute_fetchall(
            "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 1000"
        )
        alerts = [dict(r) for r in alert_rows]
    finally:
        await db.close()

    csv_bytes = generate_csv(flows, alerts)
    filename = f"traffic_report_{int(time.time())}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/pdf")
async def export_pdf(session_id: str | None = None, limit: int = Query(500, le=5000)):
    """Export full session report as PDF."""
    db = await get_db()
    try:
        flows = await get_flows(db, limit=limit, session_id=session_id)
        stats = await get_stats(db, session_id)
        alert_rows = await db.execute_fetchall(
            "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 200"
        )
        alerts = [dict(r) for r in alert_rows]
    finally:
        await db.close()

    pdf_bytes = generate_pdf(flows, alerts, stats, session_id or "")
    filename = f"traffic_report_{int(time.time())}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/summary")
async def report_summary(session_id: str | None = None):
    """Return summary stats for the reports page."""
    db = await get_db()
    try:
        stats = await get_stats(db, session_id)

        label_rows = await db.execute_fetchall(
            "SELECT flow_label, COUNT(*) as count FROM flows GROUP BY flow_label ORDER BY count DESC"
        )
        anom_rows = await db.execute_fetchall(
            "SELECT anomaly_type, COUNT(*) as count FROM flows WHERE is_anomaly=1 GROUP BY anomaly_type"
        )
        sessions = await db.execute_fetchall(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT 10"
        )
        return {
            "stats": stats,
            "label_distribution": [dict(r) for r in label_rows],
            "anomaly_breakdown": [dict(r) for r in anom_rows],
            "sessions": [dict(r) for r in sessions],
        }
    finally:
        await db.close()
