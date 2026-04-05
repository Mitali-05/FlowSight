import asyncio
import logging
import time
import ipaddress
import httpx
from config import GEOIP_API_URL, GEOIP_CACHE_TTL, GEOIP_BATCH_SIZE

logger = logging.getLogger(__name__)
_cache: dict = {}

# Hardcoded geo data for all simulation IPs — map appears immediately
KNOWN_GEOIP = {
    "8.8.8.8":          {"country": "United States", "city": "Mountain View",  "lat": 37.386,  "lon": -122.084},
    "8.8.4.4":          {"country": "United States", "city": "Mountain View",  "lat": 37.386,  "lon": -122.084},
    "1.1.1.1":          {"country": "Australia",     "city": "Sydney",         "lat": -33.868, "lon":  151.209},
    "1.0.0.1":          {"country": "Australia",     "city": "Sydney",         "lat": -33.868, "lon":  151.209},
    "216.58.214.46":    {"country": "United States", "city": "Mountain View",  "lat": 37.386,  "lon": -122.084},
    "142.250.80.46":    {"country": "United States", "city": "New York",       "lat": 40.714,  "lon":  -74.006},
    "151.101.1.140":    {"country": "United States", "city": "San Francisco",  "lat": 37.775,  "lon": -122.418},
    "104.16.133.229":   {"country": "United States", "city": "San Jose",       "lat": 37.339,  "lon": -121.894},
    "52.94.236.248":    {"country": "United States", "city": "Ashburn",        "lat": 39.043,  "lon":  -77.487},
    "185.60.216.35":    {"country": "Ireland",       "city": "Dublin",         "lat": 53.333,  "lon":   -6.249},
    "31.13.64.35":      {"country": "Ireland",       "city": "Dublin",         "lat": 53.333,  "lon":   -6.249},
    "172.217.14.238":   {"country": "United States", "city": "Chicago",        "lat": 41.850,  "lon":  -87.650},
    "13.107.42.14":     {"country": "United States", "city": "Redmond",        "lat": 47.674,  "lon": -122.121},
    "204.79.197.200":   {"country": "United States", "city": "Boydton",        "lat": 36.667,  "lon":  -78.388},
    "17.253.144.10":    {"country": "United States", "city": "Cupertino",      "lat": 37.323,  "lon": -122.032},
    "140.82.112.3":     {"country": "United States", "city": "San Francisco",  "lat": 37.775,  "lon": -122.418},
    "151.101.65.69":    {"country": "United States", "city": "San Francisco",  "lat": 37.775,  "lon": -122.418},
    "199.232.68.25":    {"country": "United States", "city": "Seattle",        "lat": 47.606,  "lon": -122.332},
    "91.108.4.1":       {"country": "Netherlands",   "city": "Amsterdam",      "lat": 52.374,  "lon":    4.890},
    "149.154.167.50":   {"country": "Netherlands",   "city": "Amsterdam",      "lat": 52.374,  "lon":    4.890},
    "74.125.24.138":    {"country": "United States", "city": "Atlanta",        "lat": 33.749,  "lon":  -84.388},
    "69.147.82.60":     {"country": "United States", "city": "Sunnyvale",      "lat": 37.369,  "lon": -122.036},
    "23.79.237.139":    {"country": "United States", "city": "Cambridge",      "lat": 42.360,  "lon":  -71.058},
    "10.99.0.1":        {"country": "Private",       "city": "Local",          "lat":  0.0,    "lon":    0.0},
    "103.21.244.0":     {"country": "India", "city": "Mumbai",    "lat": 19.076, "lon": 72.877},
    "122.160.0.1":      {"country": "India", "city": "Delhi",     "lat": 28.614, "lon": 77.209},
    "49.44.64.1":       {"country": "India", "city": "Bangalore", "lat": 12.971, "lon": 77.594},
    "117.18.232.240":   {"country": "India", "city": "Mumbai",    "lat": 19.076, "lon": 72.877},
    "202.83.21.1":      {"country": "India", "city": "Chennai",   "lat": 13.082, "lon": 80.270},
    "103.1.206.1":      {"country": "India", "city": "Hyderabad", "lat": 17.385, "lon": 78.486},
}

PRIVATE_RESULT = {"country": "Private", "city": "Local", "lat": 0.0, "lon": 0.0}


def _is_private(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
        return a.is_private or a.is_loopback or a.is_multicast or a.is_unspecified
    except ValueError:
        return False


def _get_cached(ip: str):
    if ip in _cache:
        data, expiry = _cache[ip]
        if time.time() < expiry:
            return data
        del _cache[ip]
    return None


def _set_cache(ip: str, data: dict):
    _cache[ip] = (data, time.time() + GEOIP_CACHE_TTL)


class GeoIPService:
    def __init__(self):
        self._client = None
        self._semaphore = asyncio.Semaphore(3)

    async def start(self):
        self._client = httpx.AsyncClient(timeout=4.0)

    async def stop(self):
        if self._client:
            await self._client.aclose()

    async def lookup(self, ip: str) -> dict:
        if _is_private(ip):
            return PRIVATE_RESULT.copy()
        if ip in KNOWN_GEOIP:
            return KNOWN_GEOIP[ip]
        cached = _get_cached(ip)
        if cached:
            return cached
        result = await self._fetch_batch([ip])
        return result.get(ip, {})

    async def lookup_batch(self, ips: list[str]) -> dict:
        result  = {}
        to_fetch = []

        for ip in ips:
            if _is_private(ip):
                result[ip] = PRIVATE_RESULT.copy()
                continue
            if ip in KNOWN_GEOIP:
                result[ip] = KNOWN_GEOIP[ip]
                continue
            cached = _get_cached(ip)
            if cached:
                result[ip] = cached
            else:
                to_fetch.append(ip)

        if not to_fetch:
            return result

        for i in range(0, len(to_fetch), GEOIP_BATCH_SIZE):
            fetched = await self._fetch_batch(to_fetch[i:i + GEOIP_BATCH_SIZE])
            result.update(fetched)

        return result

    async def _fetch_batch(self, ips: list[str]) -> dict:
        if not self._client:
            return {}
        payload = [{"query": ip, "fields": "status,country,city,lat,lon,query"} for ip in ips]
        async with self._semaphore:
            try:
                resp = await self._client.post(GEOIP_API_URL, json=payload)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.debug(f"GeoIP API error: {e}")
                return {}
        result = {}
        for item in data:
            if item.get("status") != "success":
                continue
            ip  = item.get("query", "")
            geo = {
                "country": item.get("country", ""),
                "city":    item.get("city",    ""),
                "lat":     float(item.get("lat", 0)),
                "lon":     float(item.get("lon", 0)),
            }
            _set_cache(ip, geo)
            result[ip] = geo
        return result