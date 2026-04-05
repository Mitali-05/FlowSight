from fastapi import APIRouter, Query, HTTPException
from database import get_db

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/")
async def list_alerts(
    limit: int = Query(50, ge=1, le=500),
    severity: str | None = None,
    unacknowledged_only: bool = False,
):
    db = await get_db()
    try:
        conditions = []
        params = []
        if severity:
            conditions.append("severity = ?")
            params.append(severity)
        if unacknowledged_only:
            conditions.append("acknowledged = 0")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)
        rows = await db.execute_fetchall(
            f"SELECT * FROM alerts {where} ORDER BY timestamp DESC LIMIT ?",
            params,
        )
        return {"alerts": [dict(r) for r in rows]}
    finally:
        await db.close()


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    db = await get_db()
    try:
        await db.execute(
            "UPDATE alerts SET acknowledged=1 WHERE id=?", [alert_id]
        )
        await db.commit()
        return {"status": "acknowledged"}
    finally:
        await db.close()


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int):
    db = await get_db()
    try:
        await db.execute("DELETE FROM alerts WHERE id=?", [alert_id])
        await db.commit()
        return {"status": "deleted"}
    finally:
        await db.close()


@router.get("/summary")
async def alert_summary():
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            """
            SELECT severity, COUNT(*) as count
            FROM alerts
            WHERE acknowledged = 0
            GROUP BY severity
            """
        )
        return {"summary": {r["severity"]: r["count"] for r in rows}}
    finally:
        await db.close()
