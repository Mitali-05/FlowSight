import numpy as np

FEATURE_NAMES = [
    "duration",
    "packet_count",
    "byte_count",
    "avg_pkt_size",
    "max_pkt_size",
    "min_pkt_size",
    "inter_arrival",
    "bytes_per_second",
    "packets_per_second",
    "src_port",
    "dst_port",
    "is_tcp",
    "is_udp",
    "is_icmp",
    "port_entropy",
    "pkt_size_variance",
    "large_pkt_ratio",
    "small_pkt_ratio",
]


def extract_features(flow: dict) -> np.ndarray:
    """
    Convert a flow dict into a feature vector for ML inference.
    
    Args:
        flow: dict with keys matching FlowRecord fields
    
    Returns:
        np.ndarray shape (1, 18) — ready for model.predict()
    """
    duration = max(flow.get("duration", 0.001), 0.001)
    packet_count = max(flow.get("packet_count", 1), 1)
    byte_count = flow.get("byte_count", 0)
    avg_pkt_size = flow.get("avg_pkt_size", 0)
    max_pkt_size = flow.get("max_pkt_size", 0)
    min_pkt_size = flow.get("min_pkt_size", 0)
    inter_arrival = flow.get("inter_arrival", 0)
    src_port = flow.get("src_port", 0)
    dst_port = flow.get("dst_port", 0)
    protocol = str(flow.get("protocol", "")).upper()

    bytes_per_second = byte_count / duration
    packets_per_second = packet_count / duration
    is_tcp = 1 if protocol == "TCP" else 0
    is_udp = 1 if protocol == "UDP" else 0
    is_icmp = 1 if protocol == "ICMP" else 0

    port_entropy = _port_entropy(src_port, dst_port)
    pkt_size_variance = _pkt_size_variance(avg_pkt_size, max_pkt_size, min_pkt_size)

    large_pkt_ratio = _estimate_large_ratio(avg_pkt_size, max_pkt_size)
    small_pkt_ratio = _estimate_small_ratio(avg_pkt_size, min_pkt_size)

    features = np.array([[
        duration,
        packet_count,
        byte_count,
        avg_pkt_size,
        max_pkt_size,
        min_pkt_size,
        inter_arrival,
        bytes_per_second,
        packets_per_second,
        src_port,
        dst_port,
        is_tcp,
        is_udp,
        is_icmp,
        port_entropy,
        pkt_size_variance,
        large_pkt_ratio,
        small_pkt_ratio,
    ]], dtype=np.float32)

    features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
    return features


def _port_entropy(src_port: int, dst_port: int) -> float:
    """
    Simple port entropy: well-known ports (< 1024) = low entropy,
    ephemeral (> 49152) = high entropy.
    """
    def port_score(p):
        if p < 1024:
            return 0.1
        elif p < 10000:
            return 0.5
        elif p < 49152:
            return 0.7
        else:
            return 1.0

    return (port_score(src_port) + port_score(dst_port)) / 2.0


def _pkt_size_variance(avg: float, max_s: int, min_s: int) -> float:
    """Estimate variance from range statistics."""
    if avg <= 0:
        return 0.0
    spread = max_s - min_s
    return (spread / avg) if avg > 0 else 0.0


def _estimate_large_ratio(avg: float, max_s: int) -> float:
    """Estimate ratio of large packets (> 1000 bytes)."""
    if max_s == 0:
        return 0.0
    # If avg is close to max and max > 1000, likely many large packets
    if avg > 1000:
        return min(1.0, avg / 1400.0)
    return 0.0


def _estimate_small_ratio(avg: float, min_s: int) -> float:
    """Estimate ratio of small packets (< 100 bytes)."""
    if avg <= 0:
        return 0.0
    if avg < 100:
        return 1.0
    if min_s < 100 and avg < 300:
        return 0.5
    return 0.0
