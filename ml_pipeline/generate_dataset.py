import csv
import random
import numpy as np
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent / "dataset.csv"
N_SAMPLES = 50_000
random.seed(42)
np.random.seed(42)


CLASSES = {
    "HTTP": {
        "weight": 0.25,
        "duration":        ("lognormal", 1.5, 1.0),
        "packet_count":    ("lognormal", 3.0, 1.2),
        "byte_count":      ("lognormal", 9.0, 1.5),
        "avg_pkt_size":    ("normal",    700, 200),
        "max_pkt_size":    ("normal",    1400, 100),
        "min_pkt_size":    ("normal",    64, 20),
        "inter_arrival":   ("lognormal", -2.0, 1.0),
        "dst_port_choices": [80, 443, 8080, 8443],
        "protocol":        "TCP",
    },
    "DNS": {
        "weight": 0.15,
        "duration":        ("lognormal", -1.0, 0.5),
        "packet_count":    ("normal",    2, 1),
        "byte_count":      ("normal",    200, 80),
        "avg_pkt_size":    ("normal",    100, 30),
        "max_pkt_size":    ("normal",    200, 50),
        "min_pkt_size":    ("normal",    60, 10),
        "inter_arrival":   ("lognormal", -3.0, 0.5),
        "dst_port_choices": [53],
        "protocol":        "DNS",
    },
    "Video_Streaming": {
        "weight": 0.20,
        "duration":        ("lognormal", 4.0, 0.8),
        "packet_count":    ("lognormal", 5.5, 1.0),
        "byte_count":      ("lognormal", 13.0, 1.0),
        "avg_pkt_size":    ("normal",    1200, 150),
        "max_pkt_size":    ("normal",    1450, 50),
        "min_pkt_size":    ("normal",    100, 30),
        "inter_arrival":   ("lognormal", -3.5, 0.5),
        "dst_port_choices": [443, 80, 1935],
        "protocol":        "TCP",
    },
    "VoIP": {
        "weight": 0.10,
        "duration":        ("lognormal", 3.5, 1.0),
        "packet_count":    ("lognormal", 5.0, 0.8),
        "byte_count":      ("lognormal", 8.0, 1.0),
        "avg_pkt_size":    ("normal",    200, 60),
        "max_pkt_size":    ("normal",    400, 80),
        "min_pkt_size":    ("normal",    60, 15),
        "inter_arrival":   ("lognormal", -4.0, 0.3),
        "dst_port_choices": [5060, 5004, 5005, 4569],
        "protocol":        "UDP",
    },
    "Gaming": {
        "weight": 0.10,
        "duration":        ("lognormal", 4.5, 1.0),
        "packet_count":    ("lognormal", 6.0, 1.0),
        "byte_count":      ("lognormal", 9.5, 1.2),
        "avg_pkt_size":    ("normal",    250, 80),
        "max_pkt_size":    ("normal",    600, 150),
        "min_pkt_size":    ("normal",    50, 20),
        "inter_arrival":   ("lognormal", -4.5, 0.4),
        "dst_port_choices": [3074, 27015, 7777, 3478],
        "protocol":        "UDP",
    },
    "Torrent": {
        "weight": 0.10,
        "duration":        ("lognormal", 5.0, 1.0),
        "packet_count":    ("lognormal", 6.5, 1.2),
        "byte_count":      ("lognormal", 12.0, 1.5),
        "avg_pkt_size":    ("normal",    900, 200),
        "max_pkt_size":    ("normal",    1400, 100),
        "min_pkt_size":    ("normal",    100, 40),
        "inter_arrival":   ("lognormal", -2.5, 0.8),
        "dst_port_choices": [6881, 6882, 51413],
        "protocol":        "TCP",
    },
    "Unknown": {
        "weight": 0.10,
        "duration":        ("lognormal", 1.0, 1.5),
        "packet_count":    ("lognormal", 2.0, 1.5),
        "byte_count":      ("lognormal", 7.0, 2.0),
        "avg_pkt_size":    ("normal",    400, 300),
        "max_pkt_size":    ("normal",    800, 400),
        "min_pkt_size":    ("normal",    64, 30),
        "inter_arrival":   ("lognormal", -1.5, 1.5),
        "dst_port_choices": list(range(1024, 60000)),
        "protocol":        "TCP",
    },
}


def sample(dist_spec):
    """Sample from a distribution spec tuple."""
    dist, *params = dist_spec
    if dist == "normal":
        val = np.random.normal(params[0], params[1])
    elif dist == "lognormal":
        val = np.random.lognormal(params[0], params[1])
    else:
        val = params[0]
    return max(0.0, float(val))


def generate_flow(label: str, spec: dict) -> dict:
    """Generate one synthetic flow with realistic feature values."""
    duration = max(sample(spec["duration"]), 0.001)
    packet_count = max(int(sample(spec["packet_count"])), 1)
    byte_count = max(int(sample(spec["byte_count"])), 1)
    avg_pkt_size = max(sample(spec["avg_pkt_size"]), 10)
    max_pkt_size = max(int(sample(spec["max_pkt_size"])), int(avg_pkt_size))
    min_pkt_size = min(max(int(sample(spec["min_pkt_size"])), 1), int(avg_pkt_size))
    inter_arrival = max(sample(spec["inter_arrival"]), 0.0001)

    bytes_per_second = byte_count / duration
    packets_per_second = packet_count / duration

    protocol = spec["protocol"]
    is_tcp = 1 if protocol == "TCP" else 0
    is_udp = 1 if protocol == "UDP" else 0
    is_icmp = 1 if protocol == "ICMP" else 0
    if protocol == "DNS":
        is_udp = 1

    dst_port = random.choice(spec["dst_port_choices"])
    src_port = random.randint(1024, 65535)

    # Port entropy
    def port_score(p):
        if p < 1024: return 0.1
        elif p < 10000: return 0.5
        elif p < 49152: return 0.7
        else: return 1.0
    port_entropy = (port_score(src_port) + port_score(dst_port)) / 2.0

    # Packet size variance (normalized)
    spread = max_pkt_size - min_pkt_size
    pkt_size_variance = (spread / avg_pkt_size) if avg_pkt_size > 0 else 0.0

    # Large/small ratios
    large_pkt_ratio = min(1.0, avg_pkt_size / 1400.0) if avg_pkt_size > 800 else 0.0
    small_pkt_ratio = 1.0 if avg_pkt_size < 100 else (0.5 if avg_pkt_size < 300 else 0.0)

    # Add small noise to all numeric features
    noise = lambda x, pct=0.05: x * (1 + np.random.uniform(-pct, pct))

    return {
        "label": label,
        "duration": round(noise(duration), 4),
        "packet_count": max(1, int(noise(packet_count, 0.1))),
        "byte_count": max(1, int(noise(byte_count, 0.1))),
        "avg_pkt_size": round(noise(avg_pkt_size), 2),
        "max_pkt_size": max_pkt_size,
        "min_pkt_size": min_pkt_size,
        "inter_arrival": round(noise(inter_arrival), 6),
        "bytes_per_second": round(noise(bytes_per_second), 2),
        "packets_per_second": round(noise(packets_per_second), 4),
        "src_port": src_port,
        "dst_port": dst_port,
        "is_tcp": is_tcp,
        "is_udp": is_udp,
        "is_icmp": is_icmp,
        "port_entropy": round(port_entropy, 4),
        "pkt_size_variance": round(pkt_size_variance, 4),
        "large_pkt_ratio": round(large_pkt_ratio, 4),
        "small_pkt_ratio": round(small_pkt_ratio, 4),
    }


def main():
    print(f"Generating {N_SAMPLES} synthetic flow records...")

    labels = list(CLASSES.keys())
    weights = [CLASSES[l]["weight"] for l in labels]
    chosen_labels = random.choices(labels, weights=weights, k=N_SAMPLES)

    rows = []
    for i, label in enumerate(chosen_labels):
        flow = generate_flow(label, CLASSES[label])
        rows.append(flow)
        if (i + 1) % 10000 == 0:
            print(f"  {i+1}/{N_SAMPLES} flows generated...")

    fieldnames = [
        "label", "duration", "packet_count", "byte_count", "avg_pkt_size",
        "max_pkt_size", "min_pkt_size", "inter_arrival", "bytes_per_second",
        "packets_per_second", "src_port", "dst_port",
        "is_tcp", "is_udp", "is_icmp",
        "port_entropy", "pkt_size_variance", "large_pkt_ratio", "small_pkt_ratio",
    ]

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    from collections import Counter
    dist = Counter(chosen_labels)
    print(f"\nDataset saved to: {OUTPUT_PATH}")
    print(f"Total samples: {N_SAMPLES}")
    print("\nClass distribution:")
    for label, count in sorted(dist.items(), key=lambda x: -x[1]):
        print(f"  {label:<20} {count:>6}  ({count/N_SAMPLES*100:.1f}%)")


if __name__ == "__main__":
    main()
