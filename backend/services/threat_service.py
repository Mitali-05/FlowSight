from config import SUSPICIOUS_PORTS, HIGH_BANDWIDTH_THRESHOLD


def compute_threat_score(flow: dict) -> int:
    """
    Compute a composite threat score from 0 (benign) to 100 (critical threat).
    
    Components:
    - Anomaly score:         0-40 pts
    - Suspicious ports:      0-20 pts
    - High bandwidth:        0-15 pts
    - DDoS indicators:       0-15 pts
    - Suspicious IP/pattern: 0-10 pts
    """
    score = 0

    anomaly_score = flow.get("anomaly_score", 0.0)
    is_anomaly = flow.get("is_anomaly", False)
    anomaly_type = flow.get("anomaly_type", "")

    if is_anomaly:
        anomaly_contrib = int((-anomaly_score + 1) / 2 * 40)
        score += min(40, max(0, anomaly_contrib))

        if anomaly_type == "ddos":
            score += 20
        elif anomaly_type == "port_scan":
            score += 15
        elif anomaly_type == "syn_scan":
            score += 10

    dst_port = flow.get("dst_port", 0)
    src_port = flow.get("src_port", 0)

    if dst_port in SUSPICIOUS_PORTS or src_port in SUSPICIOUS_PORTS:
        score += 20
    elif dst_port > 50000 and flow.get("avg_pkt_size", 0) < 100:
        score += 10

    byte_count = flow.get("byte_count", 0)
    if byte_count > HIGH_BANDWIDTH_THRESHOLD:
        score += 15
    elif byte_count > HIGH_BANDWIDTH_THRESHOLD / 2:
        score += 7

    duration = max(flow.get("duration", 1.0), 0.001)
    packet_count = flow.get("packet_count", 0)
    pps = packet_count / duration

    if pps > 1000:
        score += 15
    elif pps > 500:
        score += 8
    elif pps > 200:
        score += 4

    label = flow.get("flow_label", "")
    if label == "Unknown":
        score += 5
    if label == "Torrent":
        score += 5

    protocol = flow.get("protocol", "")
    if protocol == "ICMP" and packet_count > 100:
        score += 5

    return min(100, max(0, score))


def get_severity_label(score: int) -> str:
    """Convert numeric score to severity category."""
    if score >= 80:
        return "critical"
    elif score >= 60:
        return "high"
    elif score >= 40:
        return "medium"
    elif score >= 20:
        return "low"
    return "info"
