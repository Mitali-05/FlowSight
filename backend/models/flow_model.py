from pydantic import BaseModel, Field
from typing import Optional
import time


class FlowRecord(BaseModel):
    """Fully processed flow record sent to DB and WebSocket clients."""
    id: Optional[int] = None
    timestamp: float = Field(default_factory=time.time)
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    duration: float = 0.0
    packet_count: int = 0
    byte_count: int = 0
    avg_pkt_size: float = 0.0
    max_pkt_size: int = 0
    min_pkt_size: int = 0
    inter_arrival: float = 0.0
    flow_label: str = "Unknown"
    app_fingerprint: str = ""
    anomaly_score: float = 0.0
    is_anomaly: bool = False
    anomaly_type: str = ""
    threat_score: int = 0
    src_country: str = ""
    src_city: str = ""
    src_lat: float = 0.0
    src_lon: float = 0.0
    dst_country: str = ""
    dst_lat: float = 0.0  
    dst_lon: float = 0.0  
    session_id: str = ""

    def to_db_dict(self) -> dict:
        d = self.model_dump()
        d["is_anomaly"] = int(d["is_anomaly"])
        return d


class AlertRecord(BaseModel):
    id: Optional[int] = None
    timestamp: float = Field(default_factory=time.time)
    alert_type: str
    severity: str  # "low" | "medium" | "high" | "critical"
    src_ip: str = ""
    dst_ip: str = ""
    message: str
    flow_id: Optional[int] = None
    acknowledged: bool = False


class CaptureStartRequest(BaseModel):
    interface: str
    session_id: Optional[str] = None


class DashboardStats(BaseModel):
    total_flows: int = 0
    total_bytes: int = 0
    total_packets: int = 0
    anomaly_count: int = 0
    avg_threat: float = 0.0
    packets_per_second: float = 0.0
    bytes_per_second: float = 0.0
    active_flows: int = 0


class ProtocolDistribution(BaseModel):
    protocol: str
    count: int
    percentage: float


class TopTalker(BaseModel):
    ip: str
    bytes: int
    packets: int
    country: str = ""


class GeoIPPoint(BaseModel):
    src_ip: str
    lat: float
    lon: float
    country: str
    city: str
    threat_score: int
    flow_label: str
