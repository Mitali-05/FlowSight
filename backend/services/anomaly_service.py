import pickle
import logging
import numpy as np
from config import ANOMALY_DETECTOR_PATH, ANOMALY_THRESHOLD, SUSPICIOUS_PORTS

logger = logging.getLogger(__name__)


class AnomalyDetectionService:
    """
    Uses a pre-trained Isolation Forest to detect anomalous flows.
    Also applies rule-based heuristics for port scans and DDoS.
    """

    def __init__(self):
        self.model = None
        self._port_scan_tracker: dict[str, set] = {} 
        self._ddos_tracker: dict[str, list] = {} 
        self._loaded = False

    def load(self):
        """Load Isolation Forest model from disk."""
        try:
            if ANOMALY_DETECTOR_PATH.exists():
                with open(ANOMALY_DETECTOR_PATH, "rb") as f:
                    self.model = pickle.load(f)
                logger.info(f"Loaded anomaly detector from {ANOMALY_DETECTOR_PATH}")
            else:
                logger.warning("Anomaly detector not found — using heuristics only")
            self._loaded = True
        except Exception as e:
            logger.error(f"Failed to load anomaly detector: {e}")

    def analyze(self, flow: dict) -> tuple[float, bool, str]:
        """
        Analyze a flow for anomalies.
        
        Returns:
            (anomaly_score, is_anomaly, anomaly_type)
            score: -1.0 (definitely anomaly) to 1.0 (definitely normal)
        """

        rule_result = self._rule_check(flow)
        if rule_result[1]:
            return rule_result

        if self.model is not None:
            return self._ml_check(flow)

        return (1.0, False, "")

    def _ml_check(self, flow: dict) -> tuple[float, bool, str]:
        """Run Isolation Forest on flow features."""
        try:
            from utils.feature_extractor import extract_features
            features = extract_features(flow)
            score = float(self.model.decision_function(features)[0])
            is_anomaly = score < ANOMALY_THRESHOLD
            anomaly_type = "statistical_anomaly" if is_anomaly else ""
            return (score, is_anomaly, anomaly_type)
        except Exception as e:
            logger.debug(f"Anomaly ML check error: {e}")
            return (0.0, False, "")

    def _rule_check(self, flow: dict) -> tuple[float, bool, str]:
        """Heuristic checks for known attack patterns."""
        src_ip = flow.get("src_ip", "")
        dst_ip = flow.get("dst_ip", "")
        dst_port = flow.get("dst_port", 0)
        src_port = flow.get("src_port", 0)
        packet_count = flow.get("packet_count", 0)
        byte_count = flow.get("byte_count", 0)
        duration = flow.get("duration", 1)
        protocol = flow.get("protocol", "")

        if src_ip not in self._port_scan_tracker:
            self._port_scan_tracker[src_ip] = set()
        self._port_scan_tracker[src_ip].add(dst_port)

        if len(self._port_scan_tracker[src_ip]) > 20:
            # Reset after detection to avoid repeated alerts
            self._port_scan_tracker[src_ip] = set()
            return (-0.8, True, "port_scan")

        if duration > 0:
            pps = packet_count / duration
            if pps > 1000 and protocol == "UDP":
                return (-0.9, True, "ddos")
            if pps > 500 and packet_count > 5000:
                return (-0.85, True, "ddos")

        if dst_port in SUSPICIOUS_PORTS or src_port in SUSPICIOUS_PORTS:
            return (-0.3, True, "suspicious_port")

        if duration > 0 and byte_count / duration > 100_000_000:  # 100MB/s
            return (-0.6, True, "spike")

        if protocol == "TCP" and packet_count <= 2 and duration < 0.1:
            return (-0.4, True, "syn_scan")

        return (0.5, False, "")

    def analyze_batch(self, flows: list[dict]) -> list[tuple[float, bool, str]]:
        """Analyze multiple flows efficiently."""
        results = []
        for flow in flows:
            results.append(self.analyze(flow))
        return results
