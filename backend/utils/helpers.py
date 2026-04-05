import time
import hashlib
import ipaddress


def format_bytes(b: int) -> str:
    """Human-readable byte count."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def is_private_ip(ip: str) -> bool:
    """Check if IP is RFC-1918 private/loopback."""
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_multicast or addr.is_unspecified
    except ValueError:
        return False


def make_session_id() -> str:
    """Generate a short human-readable session ID."""
    ts = str(time.time()).encode()
    h = hashlib.sha256(ts).hexdigest()[:8]
    return h


def clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b != 0 else default
