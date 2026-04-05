import asyncio
import logging
import time
import uuid
from fastapi import APIRouter, HTTPException

from models.flow_model import CaptureStartRequest
from services.capture_service import PacketCaptureService, list_interfaces
from services.flow_aggregator import FlowAggregator
from services.ml_service import MLClassifierService
from services.anomaly_service import AnomalyDetectionService
from services.geoip_service import GeoIPService
from services.threat_service import compute_threat_score
from services.alert_service import AlertService
from services.fingerprint_service import fingerprint_app
from routers.websocket import manager, record_flow, record_packet
from database import get_db, bulk_insert_flows, insert_alert
from config import FLOW_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/capture", tags=["capture"])

_packet_queue: asyncio.Queue             = asyncio.Queue(maxsize=10_000)
_capture_service: PacketCaptureService | None = None
_aggregator    = FlowAggregator(flow_timeout=FLOW_TIMEOUT_SECONDS)
_ml_service    = MLClassifierService()
_anomaly_service  = AnomalyDetectionService()
_geoip_service    = GeoIPService()
_alert_service    = AlertService()

_current_session_id  = ""
_capture_running     = False
_processing_task: asyncio.Task | None  = None
_flush_task: asyncio.Task | None       = None
_force_flush_task: asyncio.Task | None = None


async def initialize_services():
    global _capture_service
    loop = asyncio.get_event_loop()
    _capture_service = PacketCaptureService(_packet_queue, loop)
    _ml_service.load()
    _anomaly_service.load()
    await _geoip_service.start()
    logger.info("All services initialized")


@router.get("/interfaces")
async def get_interfaces():
    return {"interfaces": list_interfaces()}


@router.post("/start")
async def start_capture(req: CaptureStartRequest):
    global _capture_running, _current_session_id
    global _processing_task, _flush_task, _force_flush_task

    if _capture_running:
        raise HTTPException(400, "Capture already running. Stop it first.")

    _current_session_id = req.session_id or str(uuid.uuid4())[:8]
    _capture_service.start(req.interface)
    _capture_running = True

    _processing_task  = asyncio.create_task(_process_packets_loop(_current_session_id))
    _flush_task       = asyncio.create_task(_flush_expired_flows_loop(_current_session_id))
    _force_flush_task = asyncio.create_task(_force_flush_loop(_current_session_id))

    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO sessions (id, started_at, interface) VALUES (?,?,?)",
            (_current_session_id, time.time(), req.interface),
        )
        await db.commit()
    finally:
        await db.close()

    logger.info(f"Capture started: session={_current_session_id} iface={req.interface}")
    return {"status": "started", "session_id": _current_session_id, "interface": req.interface}


@router.post("/stop")
async def stop_capture():
    global _capture_running
    if not _capture_running:
        raise HTTPException(400, "No capture is running")

    _capture_running = False
    _capture_service.stop()

    for task in [_processing_task, _flush_task, _force_flush_task]:
        if task:
            task.cancel()

    remaining = _aggregator.flush_all(_current_session_id)
    if remaining:
        await _process_flow_batch(remaining)

    db = await get_db()
    try:
        await db.execute(
            "UPDATE sessions SET ended_at=? WHERE id=?",
            (time.time(), _current_session_id),
        )
        await db.commit()
    finally:
        await db.close()

    return {"status": "stopped", "session_id": _current_session_id,
            "total_packets": _capture_service.packet_count}


@router.get("/status")
async def get_status():
    return {
        "running":      _capture_running,
        "session_id":   _current_session_id,
        "packet_count": _capture_service.packet_count if _capture_service else 0,
        "active_flows": _aggregator.active_flow_count,
        "queue_size":   _packet_queue.qsize(),
    }



async def _process_packets_loop(session_id: str):
    batch = []
    while True:
        try:
            pkt_info = await asyncio.wait_for(_packet_queue.get(), timeout=0.1)
            batch.append(pkt_info)
            while len(batch) < 50:
                try:
                    batch.append(_packet_queue.get_nowait())
                except asyncio.QueueEmpty:
                    break

            completed_flows = []
            for pkt in batch:
                record_packet(pkt.get("size", 0))   # ← smooth chart counter
                flow = _aggregator.add_packet(pkt, session_id)
                if flow:
                    completed_flows.append(flow)
            batch.clear()

            if completed_flows:
                await _process_flow_batch(completed_flows)

        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Packet processing error: {e}")


async def _flush_expired_flows_loop(session_id: str):
    while True:
        try:
            await asyncio.sleep(2)
            expired = _aggregator.flush_expired(session_id)
            if expired:
                await _process_flow_batch(expired)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Flush error: {e}")


async def _force_flush_loop(session_id: str):
    """Force-complete all flows every 4s so dashboard stays live."""
    while True:
        try:
            await asyncio.sleep(4)
            active = _aggregator.flush_all(session_id)
            if active:
                await _process_flow_batch(active)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Force flush error: {e}")


async def _process_flow_batch(flows: list[dict]):
    if not flows:
        return

    labels = _ml_service.classify_batch(flows)
    for flow, label in zip(flows, labels):
        flow["flow_label"] = label

    for flow, (score, is_anom, anom_type) in zip(
        flows, _anomaly_service.analyze_batch(flows)
    ):
        flow["anomaly_score"] = score
        flow["is_anomaly"]    = is_anom
        flow["anomaly_type"]  = anom_type

    for flow in flows:
        flow["app_fingerprint"] = fingerprint_app(flow)

    for flow in flows:
        flow["threat_score"] = compute_threat_score(flow)

    unique_ips = list({f["src_ip"] for f in flows} | {f["dst_ip"] for f in flows})
    geo_data = await _geoip_service.lookup_batch(unique_ips)
    for flow in flows:
        src = geo_data.get(flow["src_ip"], {})
        dst = geo_data.get(flow["dst_ip"], {})
        flow["src_country"] = src.get("country", "")
        flow["src_city"]    = src.get("city",    "")
        flow["src_lat"]     = src.get("lat",     0.0)
        flow["src_lon"]     = src.get("lon",     0.0)
        flow["dst_country"] = dst.get("country", "")
        flow["dst_city"]    = dst.get("city",    "") 
        flow["dst_lat"]     = dst.get("lat",     0.0)
        flow["dst_lon"]     = dst.get("lon",     0.0) 

    db = await get_db()
    try:
        await bulk_insert_flows(db, [{**f, "is_anomaly": int(f["is_anomaly"])} for f in flows])
    finally:
        await db.close()

    for flow in flows:
        alert = await _alert_service.evaluate_flow(flow)
        if alert:
            db = await get_db()
            try:
                await insert_alert(db, alert)
            finally:
                await db.close()
            await manager.broadcast({"type": "alert", "data": alert})

    for flow in flows:
        record_flow(flow)