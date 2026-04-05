import asyncio
import json
import logging
import time
from collections import deque
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from config import WS_BROADCAST_INTERVAL, WS_STATS_HISTORY

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)
        logger.info(f"WS connected. Total: {len(self._connections)}")

    def disconnect(self, ws: WebSocket):
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info(f"WS disconnected. Total: {len(self._connections)}")

    async def broadcast(self, message: dict):
        payload = json.dumps(message)
        dead = []
        for ws in self._connections[:]:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()
stats_history: deque = deque(maxlen=WS_STATS_HISTORY)

_pkt_counter     = 0
_byte_counter    = 0
_last_stats_time = time.time()
_recent_flows: deque        = deque(maxlen=20)
_protocol_counts: dict      = {}
_top_talkers: dict          = {}


def record_packet(size: int = 0):
    """Called per-packet from capture loop for smooth chart updates."""
    global _pkt_counter, _byte_counter
    _pkt_counter  += 1
    _byte_counter += size


def record_flow(flow: dict):
    """Called per completed flow."""
    _recent_flows.append(flow)
    label = flow.get("flow_label", "Unknown")
    _protocol_counts[label] = _protocol_counts.get(label, 0) + 1
    src_ip = flow.get("src_ip", "")
    if src_ip:
        if src_ip not in _top_talkers:
            _top_talkers[src_ip] = {
                "ip": src_ip, "bytes": 0, "packets": 0,
                "country": flow.get("src_country", ""),
            }
        _top_talkers[src_ip]["bytes"]   += flow.get("byte_count", 0)
        _top_talkers[src_ip]["packets"] += flow.get("packet_count", 0)


async def broadcast_loop():
    global _pkt_counter, _byte_counter, _last_stats_time

    while True:
        await asyncio.sleep(WS_BROADCAST_INTERVAL)
        if manager.connection_count == 0:
            continue

        now     = time.time()
        elapsed = max(now - _last_stats_time, 0.001)
        pps     = _pkt_counter  / elapsed
        bps     = _byte_counter / elapsed
        _pkt_counter  = 0
        _byte_counter = 0
        _last_stats_time = now

        stats_history.append({"t": now, "pps": round(pps, 2), "bps": round(bps, 2)})

        total_labels = sum(_protocol_counts.values()) or 1
        proto_dist = [
            {"name": k, "count": v, "pct": round(v / total_labels * 100, 1)}
            for k, v in sorted(_protocol_counts.items(), key=lambda x: -x[1])[:10]
        ]
        top_talkers = sorted(_top_talkers.values(), key=lambda x: x["bytes"], reverse=True)[:10]

        # Live capture stats
        active_flows = queue_size = total_packets = 0
        capturing = False
        try:
            from routers.capture import _aggregator, _capture_service, _packet_queue, _capture_running
            if _aggregator:      active_flows  = _aggregator.active_flow_count
            if _packet_queue:    queue_size    = _packet_queue.qsize()
            if _capture_service: total_packets = _capture_service.packet_count
            capturing = _capture_running
        except Exception:
            pass

        await manager.broadcast({
            "type": "stats",
            "data": {
                "pps":                   round(pps, 2),
                "bps":                   round(bps, 2),
                "stats_history":         list(stats_history)[-60:],
                "protocol_distribution": proto_dist,
                "top_talkers":           top_talkers,
                "recent_flows":          list(_recent_flows),
                "active_flows":          active_flows,
                "queue_size":            queue_size,
                "total_packets":         total_packets,
                "capturing":             capturing,
                "timestamp":             now,
            },
        })


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        await ws.send_text(json.dumps({"type": "connected", "data": {}}))
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                if json.loads(data).get("type") == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                await ws.send_text(json.dumps({"type": "heartbeat"}))
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception as e:
        logger.debug(f"WebSocket error: {e}")
        manager.disconnect(ws)