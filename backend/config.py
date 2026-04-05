import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
ML_DIR = BASE_DIR / "ml"
DB_PATH = BASE_DIR / "traffic.db"

DEFAULT_INTERFACE = os.getenv("CAPTURE_INTERFACE", "eth0")
FLOW_TIMEOUT_SECONDS = 8 
MAX_QUEUE_SIZE = 10_000
PACKET_BATCH_SIZE = 50 

CLASSIFIER_PATH = ML_DIR / "classifier.pkl"
ANOMALY_DETECTOR_PATH = ML_DIR / "anomaly_detector.pkl"
LABEL_ENCODER_PATH = ML_DIR / "label_encoder.pkl"

TRAFFIC_CLASSES = [
    "HTTP",
    "DNS",
    "Video_Streaming",
    "VoIP",
    "Gaming",
    "Torrent",
    "Unknown",
]

ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", "-0.1"))
ANOMALY_LABELS = {
    "port_scan": "Port Scan Detected",
    "ddos": "DDoS Pattern",
    "spike": "Abnormal Traffic Spike",
    "normal": "Normal",
}

THREAT_THRESHOLD = int(os.getenv("THREAT_THRESHOLD", "70"))

SUSPICIOUS_PORTS = {
    23, 25, 445, 1433, 1434, 3306, 3389, 4444, 5900, 6666, 6667, 6668,
    8080, 8443, 9200, 27017, 31337, 65535,
}

HIGH_BANDWIDTH_THRESHOLD = 10_000_000

GEOIP_API_URL = "http://ip-api.com/batch"
GEOIP_CACHE_TTL = 3600 
GEOIP_BATCH_SIZE = 100 

ALERT_EMAIL_ENABLED = os.getenv("ALERT_EMAIL_ENABLED", "false").lower() == "true"
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL", "admin@example.com")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

WS_BROADCAST_INTERVAL = 0.5 
WS_STATS_HISTORY = 60

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]

APP_FINGERPRINTS = {
    "Netflix": {
        "ports": {443, 80},
        "avg_pkt_size_range": (800, 1500),
        "flow_duration_min": 5,
        "byte_count_min": 500_000,
    },
    "YouTube": {
        "ports": {443, 80},
        "avg_pkt_size_range": (600, 1400),
        "flow_duration_min": 3,
        "byte_count_min": 200_000,
    },
    "Spotify": {
        "ports": {443, 4070, 57621},
        "avg_pkt_size_range": (100, 600),
        "flow_duration_min": 2,
        "byte_count_min": 10_000,
    },
    "Discord": {
        "ports": {443, 50000, 50001, 50002},
        "avg_pkt_size_range": (80, 400),
        "flow_duration_min": 1,
        "byte_count_min": 1_000,
    },
    "Zoom": {
        "ports": {8801, 8802, 443},
        "avg_pkt_size_range": (200, 1200),
        "flow_duration_min": 10,
        "byte_count_min": 100_000,
    },
    "BitTorrent": {
        "ports": {6881, 6882, 6883, 6884, 6885, 6886, 51413},
        "avg_pkt_size_range": (400, 1500),
        "flow_duration_min": 10,
        "byte_count_min": 50_000,
    },
}
