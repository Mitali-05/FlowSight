import asyncio
import logging
import time
import threading
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from scapy.all import sniff, IP, IPv6, TCP, UDP, ICMP
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False


def list_interfaces() -> list[dict]:
    if not SCAPY_AVAILABLE:
        return _simulated_interfaces()
    try:
        from scapy.arch.windows import IFACES
        result = []
        for key, iface in IFACES.items():
            try:
                result.append({
                    "name": getattr(iface, 'name', key),
                    "ip":   getattr(iface, 'ip', 'unknown') or 'unknown',
                    "desc": getattr(iface, 'description', key) or key,
                })
            except Exception:
                continue
        return result if result else _simulated_interfaces()
    except Exception:
        return _simulated_interfaces()


def _simulated_interfaces() -> list[dict]:
    return [
        {"name": "Simulated-WiFi",     "ip": "192.168.1.100"},
        {"name": "Simulated-Ethernet", "ip": "192.168.1.101"},
    ]


class PacketCaptureService:

    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self.queue         = queue
        self.loop          = loop
        self._stop_event   = threading.Event()
        self._thread       = None
        self._interface    = "simulation"
        self._packet_count = 0
        self._is_running   = False

    def start(self, interface: str):
        if self._is_running:
            return

        self._interface    = interface
        self._packet_count = 0
        self._stop_event.clear()  
        self._is_running   = True

        self._thread = threading.Thread(
            target=self._simulate_capture,
            daemon=True,
            name="PacketCapture"
        )
        self._thread.start()
        logger.info(f"Capture started on '{interface}' (simulation mode)")

    def stop(self):
        self._stop_event.set()
        self._is_running = False
        logger.info(f"Capture stopped. Total packets: {self._packet_count}")

    @property
    def is_running(self):
        return self._is_running

    @property
    def packet_count(self):
        return self._packet_count

    def _push(self, pkt_info: dict):
        try:
            asyncio.run_coroutine_threadsafe(self.queue.put(pkt_info), self.loop)
        except Exception:
            pass

    def _simulate_capture(self):
        import random
        rng = random.Random()

        SRC_IPS = ["192.168.1.10","192.168.1.25","192.168.1.42","10.0.0.5","10.0.0.12"]
        DST_IPS = [
            "8.8.8.8",          # US - Google
            "1.1.1.1",          # AU - Cloudflare  
            "216.58.214.46",    # US - Google
            "151.101.1.140",    # US - Fastly
            "104.16.133.229",   # US - Cloudflare
            "52.94.236.248",    # US - AWS
            "185.60.216.35",    # IE - Meta
            "31.13.64.35",      # IE - Facebook
            "172.217.14.238",   # US - Google
            "13.107.42.14",     # US - Microsoft
            "204.79.197.200",   # US - Microsoft
            "17.253.144.10",    # US - Apple
            "140.82.112.3",     # US - GitHub
            "151.101.65.69",    # US - Reddit
            "199.232.68.25",    # US - npm
            "91.108.4.1",       # NL - Telegram
            "149.154.167.50",   # NL - Telegram
            "74.125.24.138",    # US - Google
            "69.147.82.60",     # US - Yahoo
            "23.79.237.139",    # US - Akamai
            "103.21.244.0",     # Cloudflare India
            "122.160.0.1",      # Airtel India  
            "49.44.64.1",       # BSNL India
            "117.18.232.240",   # Reliance Jio
            "202.83.21.1",      # Tata Communications India
            "103.1.206.1",      # Hathway India
        ]

        PROFILES = [
            (443,  "TCP", (800,1400), 0.28),
            (80,   "TCP", (400,1200), 0.15),
            (53,   "DNS", (50, 200),  0.15),
            (443,  "TCP", (900,1450), 0.12),
            (5004, "UDP", (160,600),  0.08),
            (3074, "UDP", (80, 350),  0.07),
            (6881, "TCP", (600,1400), 0.05),
            (22,   "TCP", (64, 512),  0.05),
            (5060, "UDP", (200,800),  0.05),
        ]

        logger.info("Simulation thread running...")

        while not self._stop_event.is_set():
            batch = rng.randint(20, 50)

            for _ in range(batch):
                if self._stop_event.is_set():
                    break

                roll = rng.random()
                dst_port, protocol, size_range, _ = rng.choices(
                    PROFILES, weights=[p[3] for p in PROFILES]
                )[0]

                if roll < 0.008:
                    pkt = {"timestamp": time.time(), "src_ip": "10.99.0.1",
                           "dst_ip": rng.choice(DST_IPS), "src_port": 12345,
                           "dst_port": rng.randint(1, 65535), "protocol": "TCP", "size": 64}
                elif roll < 0.013:
                    pkt = {"timestamp": time.time(),
                           "src_ip": f"10.{rng.randint(1,254)}.{rng.randint(1,254)}.{rng.randint(1,254)}",
                           "dst_ip": "192.168.1.100", "src_port": rng.randint(1024,65535),
                           "dst_port": 80, "protocol": "UDP", "size": rng.randint(64,128)}
                else:
                    pkt = {"timestamp": time.time(), "src_ip": rng.choice(SRC_IPS),
                           "dst_ip": rng.choice(DST_IPS), "src_port": rng.randint(1024,65535),
                           "dst_port": dst_port, "protocol": protocol,
                           "size": rng.randint(*size_range)}

                self._packet_count += 1
                self._push(pkt)

            self._stop_event.wait(timeout=1.0)

        logger.info(f"Simulation stopped. {self._packet_count} total packets.")