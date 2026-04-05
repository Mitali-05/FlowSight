import aiosqlite
import asyncio
import logging
from pathlib import Path
from config import DB_PATH

logger = logging.getLogger(__name__)

CREATE_FLOWS_TABLE = """
CREATE TABLE IF NOT EXISTS flows (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       REAL    NOT NULL,
    src_ip          TEXT    NOT NULL,
    dst_ip          TEXT    NOT NULL,
    src_port        INTEGER NOT NULL,
    dst_port        INTEGER NOT NULL,
    protocol        TEXT    NOT NULL,
    duration        REAL    NOT NULL DEFAULT 0,
    packet_count    INTEGER NOT NULL DEFAULT 0,
    byte_count      INTEGER NOT NULL DEFAULT 0,
    avg_pkt_size    REAL    NOT NULL DEFAULT 0,
    max_pkt_size    INTEGER NOT NULL DEFAULT 0,
    min_pkt_size    INTEGER NOT NULL DEFAULT 0,
    inter_arrival   REAL    NOT NULL DEFAULT 0,
    flow_label      TEXT    NOT NULL DEFAULT 'Unknown',
    app_fingerprint TEXT    NOT NULL DEFAULT '',
    anomaly_score   REAL    NOT NULL DEFAULT 0,
    is_anomaly      INTEGER NOT NULL DEFAULT 0,
    anomaly_type    TEXT    NOT NULL DEFAULT '',
    threat_score    INTEGER NOT NULL DEFAULT 0,
    src_country     TEXT    NOT NULL DEFAULT '',
    src_city        TEXT    NOT NULL DEFAULT '',
    src_lat         REAL    NOT NULL DEFAULT 0,
    src_lon         REAL    NOT NULL DEFAULT 0,
    dst_country     TEXT    NOT NULL DEFAULT '',
    dst_lat         REAL    NOT NULL DEFAULT 0,
    dst_lon         REAL    NOT NULL DEFAULT 0,
    session_id      TEXT    NOT NULL DEFAULT ''
);
"""

CREATE_ALERTS_TABLE = """
CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   REAL    NOT NULL,
    alert_type  TEXT    NOT NULL,
    severity    TEXT    NOT NULL,
    src_ip      TEXT    NOT NULL DEFAULT '',
    dst_ip      TEXT    NOT NULL DEFAULT '',
    message     TEXT    NOT NULL,
    flow_id     INTEGER REFERENCES flows(id),
    acknowledged INTEGER NOT NULL DEFAULT 0
);
"""

CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT    PRIMARY KEY,
    started_at  REAL    NOT NULL,
    ended_at    REAL,
    interface   TEXT    NOT NULL DEFAULT '',
    total_flows INTEGER NOT NULL DEFAULT 0,
    total_bytes INTEGER NOT NULL DEFAULT 0,
    total_pkts  INTEGER NOT NULL DEFAULT 0
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_flows_timestamp ON flows(timestamp DESC);",
    "CREATE INDEX IF NOT EXISTS idx_flows_src_ip    ON flows(src_ip);",
    "CREATE INDEX IF NOT EXISTS idx_flows_label     ON flows(flow_label);",
    "CREATE INDEX IF NOT EXISTS idx_flows_anomaly   ON flows(is_anomaly);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_ts       ON alerts(timestamp DESC);",
    "CREATE INDEX IF NOT EXISTS idx_flows_session   ON flows(session_id);",
]

async def init_db():
    """Create all tables and indexes."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.execute(CREATE_FLOWS_TABLE)
        await db.execute(CREATE_ALERTS_TABLE)
        await db.execute(CREATE_SESSIONS_TABLE)
        for idx in CREATE_INDEXES:
            await db.execute(idx)
        await db.commit()
    logger.info(f"Database initialized at {DB_PATH}")


async def get_db() -> aiosqlite.Connection:
    """Return a new DB connection (use as async context manager)."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL;")
    return db



async def insert_flow(db: aiosqlite.Connection, flow: dict) -> int:
    """Insert a processed flow record. Returns inserted row ID."""
    sql = """
    INSERT INTO flows (
        timestamp, src_ip, dst_ip, src_port, dst_port, protocol,
        duration, packet_count, byte_count, avg_pkt_size,
        max_pkt_size, min_pkt_size, inter_arrival,
        flow_label, app_fingerprint,
        anomaly_score, is_anomaly, anomaly_type, threat_score,
        src_country, src_city, src_lat, src_lon, dst_country, session_id
    ) VALUES (
        :timestamp, :src_ip, :dst_ip, :src_port, :dst_port, :protocol,
        :duration, :packet_count, :byte_count, :avg_pkt_size,
        :max_pkt_size, :min_pkt_size, :inter_arrival,
        :flow_label, :app_fingerprint,
        :anomaly_score, :is_anomaly, :anomaly_type, :threat_score,
        :src_country, :src_city, :src_lat, :src_lon, :dst_country, :session_id
    )
    """
    cursor = await db.execute(sql, flow)
    await db.commit()
    return cursor.lastrowid


async def bulk_insert_flows(db, flows):
    if not flows:
        return
    sql = """
    INSERT INTO flows (
        timestamp, src_ip, dst_ip, src_port, dst_port, protocol,
        duration, packet_count, byte_count, avg_pkt_size,
        max_pkt_size, min_pkt_size, inter_arrival,
        flow_label, app_fingerprint,
        anomaly_score, is_anomaly, anomaly_type, threat_score,
        src_country, src_city, src_lat, src_lon,
        dst_country, dst_lat, dst_lon, session_id
    ) VALUES (
        :timestamp, :src_ip, :dst_ip, :src_port, :dst_port, :protocol,
        :duration, :packet_count, :byte_count, :avg_pkt_size,
        :max_pkt_size, :min_pkt_size, :inter_arrival,
        :flow_label, :app_fingerprint,
        :anomaly_score, :is_anomaly, :anomaly_type, :threat_score,
        :src_country, :src_city, :src_lat, :src_lon,
        :dst_country, :dst_lat, :dst_lon, :session_id
    )
    """
    await db.executemany(sql, flows)
    await db.commit()


async def insert_alert(db: aiosqlite.Connection, alert: dict) -> int:
    sql = """
    INSERT INTO alerts (timestamp, alert_type, severity, src_ip, dst_ip, message, flow_id)
    VALUES (:timestamp, :alert_type, :severity, :src_ip, :dst_ip, :message, :flow_id)
    """
    cursor = await db.execute(sql, alert)
    await db.commit()
    return cursor.lastrowid


async def get_flows(db, limit=100, offset=0, label=None, anomaly_only=False, session_id=None):
    """Query flows with optional filters."""
    conditions = []
    params = []
    if label:
        conditions.append("flow_label = ?")
        params.append(label)
    if anomaly_only:
        conditions.append("is_anomaly = 1")
    if session_id:
        conditions.append("session_id = ?")
        params.append(session_id)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params += [limit, offset]
    rows = await db.execute_fetchall(
        f"SELECT * FROM flows {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        params,
    )
    return [dict(r) for r in rows]


async def get_stats(db, session_id=None) -> dict:
    """Return aggregate statistics."""
    cond = "WHERE session_id = ?" if session_id else ""
    params = [session_id] if session_id else []
    row = await db.execute_fetchall(
        f"""
        SELECT
            COUNT(*)          AS total_flows,
            SUM(byte_count)   AS total_bytes,
            SUM(packet_count) AS total_packets,
            SUM(is_anomaly)   AS anomaly_count,
            AVG(threat_score) AS avg_threat
        FROM flows {cond}
        """,
        params,
    )
    return dict(row[0]) if row else {}
