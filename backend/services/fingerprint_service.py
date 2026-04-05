from config import APP_FINGERPRINTS


def fingerprint_app(flow: dict) -> str:
    dst_port = flow.get("dst_port", 0)
    src_port = flow.get("src_port", 0)
    avg_pkt_size = flow.get("avg_pkt_size", 0)
    duration = flow.get("duration", 0)
    byte_count = flow.get("byte_count", 0)

    best_match = ""
    best_score = 0

    for app_name, fingerprint in APP_FINGERPRINTS.items():
        score = 0

        fp_ports = fingerprint.get("ports", set())
        if dst_port in fp_ports or src_port in fp_ports:
            score += 3

        size_min, size_max = fingerprint.get("avg_pkt_size_range", (0, 9999))
        if size_min <= avg_pkt_size <= size_max:
            score += 2

        dur_min = fingerprint.get("flow_duration_min", 0)
        if duration >= dur_min:
            score += 1

        bytes_min = fingerprint.get("byte_count_min", 0)
        if byte_count >= bytes_min:
            score += 2

        if score > best_score:
            best_score = score
            best_match = app_name

    return best_match if best_score >= 5 else ""
