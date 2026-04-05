import time
from fastapi import APIRouter, Query
from database import get_db, get_flows, get_stats

router = APIRouter(prefix="/flows", tags=["flows"])


@router.get("/")
async def list_flows(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    label: str | None = None,
    anomaly_only: bool = False,
    session_id: str | None = None,
):
    db = await get_db()
    try:
        flows = await get_flows(db, limit, offset, label, anomaly_only, session_id)
        return {"flows": flows, "count": len(flows)}
    finally:
        await db.close()


@router.get("/stats")
async def flow_stats(session_id: str | None = None):
    db = await get_db()
    try:
        stats = await get_stats(db, session_id)
        return stats
    finally:
        await db.close()


@router.get("/geoip")
async def geoip_points(limit: int = Query(200, ge=1, le=1000)):
    """Return flows with geolocation data for map visualization."""
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """
            SELECT dst_ip    AS src_ip,
                   dst_lat   AS lat,
                   dst_lon   AS lon,
                   dst_country AS country,
                   ''        AS city,
                   threat_score,
                   flow_label
            FROM flows
            WHERE dst_lat != 0 AND dst_lon != 0
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            [limit],
        )
        return {"points": [dict(r) for r in rows]}
    finally:
        await db.close()


@router.get("/timeline")
async def traffic_timeline(hours: int = Query(1, ge=1, le=24)):
    """Return per-minute traffic counts for the last N hours."""
    since = time.time() - hours * 3600
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """
            SELECT
                CAST(timestamp / 60 AS INTEGER) * 60 AS minute,
                COUNT(*) AS flow_count,
                SUM(packet_count) AS packets,
                SUM(byte_count) AS bytes
            FROM flows
            WHERE timestamp > ?
            GROUP BY minute
            ORDER BY minute
            """,
            [since],
        )
        return {"timeline": [dict(r) for r in rows]}
    finally:
        await db.close()


@router.get("/distribution")
async def label_distribution():
    """Return traffic label distribution."""
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """
            SELECT flow_label, COUNT(*) as count, SUM(byte_count) as bytes
            FROM flows
            GROUP BY flow_label
            ORDER BY count DESC
            """
        )
        total = sum(r["count"] for r in rows)
        result = [
            {
                **dict(r),
                "percentage": round(r["count"] / total * 100, 1) if total else 0
            }
            for r in rows
        ]
        return {"distribution": result}
    finally:
        await db.close()


@router.get("/top-talkers")
async def top_talkers(limit: int = Query(10, ge=1, le=50)):
    """Return top IPs by byte volume."""
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """
            SELECT src_ip AS ip, src_country AS country,
                   SUM(byte_count) AS bytes, SUM(packet_count) AS packets
            FROM flows
            GROUP BY src_ip
            ORDER BY bytes DESC
            LIMIT ?
            """,
            [limit],
        )
        return {"top_talkers": [dict(r) for r in rows]}
    finally:
        await db.close()
