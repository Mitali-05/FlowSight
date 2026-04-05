import time
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# 5-tuple key: (src_ip, dst_ip, src_port, dst_port, protocol)
FlowKey = tuple

@dataclass
class ActiveFlow:
    """Mutable state for a flow being actively assembled."""
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    start_time: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    packet_count: int = 0
    byte_count: int = 0
    max_pkt_size: int = 0
    min_pkt_size: int = 999999
    pkt_times: list = field(default_factory=list)
    pkt_sizes: list = field(default_factory=list)

    def update(self, pkt_size: int, ts: float):
        self.packet_count += 1
        self.byte_count += pkt_size
        self.max_pkt_size = max(self.max_pkt_size, pkt_size)
        self.min_pkt_size = min(self.min_pkt_size, pkt_size)
        self.pkt_sizes.append(pkt_size)
        self.pkt_times.append(ts)
        self.last_seen = ts

    def to_flow_dict(self, session_id: str = "") -> dict:
        now = time.time()
        duration = max(self.last_seen - self.start_time, 0.001)
        avg_pkt_size = self.byte_count / max(self.packet_count, 1)

        if len(self.pkt_times) > 1:
            gaps = [self.pkt_times[i+1] - self.pkt_times[i]
                    for i in range(len(self.pkt_times)-1)]
            inter_arrival = sum(gaps) / len(gaps)
        else:
            inter_arrival = 0.0

        return {
            "timestamp": self.start_time,
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "protocol": self.protocol,
            "duration": duration,
            "packet_count": self.packet_count,
            "byte_count": self.byte_count,
            "avg_pkt_size": avg_pkt_size,
            "max_pkt_size": self.max_pkt_size,
            "min_pkt_size": self.min_pkt_size if self.packet_count > 0 else 0,
            "inter_arrival": inter_arrival,
            "flow_label": "Unknown",
            "app_fingerprint": "",
            "anomaly_score": 0.0,
            "is_anomaly": False,
            "anomaly_type": "",
            "threat_score": 0,
            "src_country": "",
            "src_city": "",
            "src_lat": 0.0,
            "src_lon": 0.0,
            "dst_country": "",
            "session_id": session_id,
        }


class FlowAggregator:
    """
    Stateful 5-tuple flow aggregator.
    
    Collects packets into flows, expires idle flows after timeout,
    and yields completed flow dicts for downstream processing.
    """

    def __init__(self, flow_timeout: float = 30.0):
        self._flows: dict[FlowKey, ActiveFlow] = {}
        self.flow_timeout = flow_timeout
        self._completed: list[dict] = []

    def _make_key(self, src_ip, dst_ip, src_port, dst_port, protocol) -> FlowKey:
        # Bidirectional: sort IPs to unify A→B and B→A into same flow
        if (src_ip, src_port) > (dst_ip, dst_port):
            src_ip, dst_ip = dst_ip, src_ip
            src_port, dst_port = dst_port, src_port
        return (src_ip, dst_ip, src_port, dst_port, protocol)

    def add_packet(self, pkt_info: dict, session_id: str = "") -> Optional[dict]:
        src_ip = pkt_info.get("src_ip", "0.0.0.0")
        dst_ip = pkt_info.get("dst_ip", "0.0.0.0")
        src_port = pkt_info.get("src_port", 0)
        dst_port = pkt_info.get("dst_port", 0)
        protocol = pkt_info.get("protocol", "TCP")
        pkt_size = pkt_info.get("size", 0)
        ts = pkt_info.get("timestamp", time.time())

        key = self._make_key(src_ip, dst_ip, src_port, dst_port, protocol)

        if key not in self._flows:
            self._flows[key] = ActiveFlow(
                src_ip=src_ip,
                dst_ip=dst_ip,
                src_port=src_port,
                dst_port=dst_port,
                protocol=protocol,
                start_time=ts,
                last_seen=ts,
            )

        self._flows[key].update(pkt_size, ts)

        return self._maybe_expire(key, session_id)

    def _maybe_expire(self, key: FlowKey, session_id: str) -> Optional[dict]:
        """If flow has been idle too long, complete and remove it."""
        flow = self._flows[key]
        age = time.time() - flow.last_seen
        if age > self.flow_timeout and flow.packet_count >= 2:
            completed = flow.to_flow_dict(session_id)
            del self._flows[key]
            return completed
        return None

    def flush_expired(self, session_id: str = "") -> list[dict]:
        """
        Scan all active flows and return those that have exceeded the timeout.
        Call this periodically (e.g., every 5 seconds).
        """
        now = time.time()
        expired_keys = [
            k for k, f in self._flows.items()
            if (now - f.last_seen) > self.flow_timeout and f.packet_count >= 2
        ]
        completed = []
        for k in expired_keys:
            completed.append(self._flows[k].to_flow_dict(session_id))
            del self._flows[k]
        if completed:
            logger.debug(f"Flushed {len(completed)} expired flows")
        return completed

    def flush_all(self, session_id: str = "") -> list[dict]:
        """Force-complete all active flows (called on capture stop)."""
        completed = [f.to_flow_dict(session_id) for f in self._flows.values()
                     if f.packet_count >= 1]
        self._flows.clear()
        return completed

    @property
    def active_flow_count(self) -> int:
        return len(self._flows)
