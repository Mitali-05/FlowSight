import asyncio
import logging
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Callable, Optional

from config import (
    THREAT_THRESHOLD,
    ALERT_EMAIL_ENABLED, ALERT_EMAIL_TO,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
)
from services.threat_service import get_severity_label

logger = logging.getLogger(__name__)


class AlertService:

    def __init__(self):
        self._pending_alerts: asyncio.Queue = asyncio.Queue()
        self._subscribers: list[asyncio.Queue] = []
        self._alert_count = 0
        self._recent_alerts: dict[str, float] = {}
        self._rate_limit_window = 60.0
        self._rate_limit_max = 10

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def evaluate_flow(self, flow: dict) -> Optional[dict]:
        threat_score = flow.get("threat_score", 0)
        is_anomaly = flow.get("is_anomaly", False)
        anomaly_type = flow.get("anomaly_type", "")
        src_ip = flow.get("src_ip", "")
        dst_ip = flow.get("dst_ip", "")

        alert = None

        if anomaly_type == "ddos":
            alert = self._make_alert(
                alert_type="DDoS",
                severity="critical",
                src_ip=src_ip,
                dst_ip=dst_ip,
                message=f"Potential DDoS attack detected from {src_ip} → {dst_ip}. "
                        f"Threat score: {threat_score}",
                flow_id=flow.get("id"),
            )
        elif anomaly_type in ("port_scan", "syn_scan"):
            alert = self._make_alert(
                alert_type="Port Scan",
                severity="high",
                src_ip=src_ip,
                dst_ip=dst_ip,
                message=f"Port scan detected from {src_ip}. "
                        f"Multiple destination ports probed.",
                flow_id=flow.get("id"),
            )
        elif threat_score >= THREAT_THRESHOLD:
            alert = self._make_alert(
                alert_type="High Threat Score",
                severity=get_severity_label(threat_score),
                src_ip=src_ip,
                dst_ip=dst_ip,
                message=f"High threat score ({threat_score}/100) on flow "
                        f"{src_ip}:{flow.get('src_port')} → {dst_ip}:{flow.get('dst_port')} "
                        f"[{flow.get('flow_label', 'Unknown')}]",
                flow_id=flow.get("id"),
            )

        if alert:
            key = f"{alert['alert_type']}:{src_ip}"
            if not self._is_rate_limited(key):
                await self._broadcast(alert)
                if ALERT_EMAIL_ENABLED and alert["severity"] in ("high", "critical"):
                    asyncio.create_task(self._send_email(alert))
                return alert

        return None

    def _make_alert(self, alert_type, severity, src_ip, dst_ip, message, flow_id=None) -> dict:
        self._alert_count += 1
        return {
            "id": self._alert_count,
            "timestamp": time.time(),
            "alert_type": alert_type,
            "severity": severity,
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "message": message,
            "flow_id": flow_id,
            "acknowledged": False,
        }

    def _is_rate_limited(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self._rate_limit_window
        self._recent_alerts = {k: v for k, v in self._recent_alerts.items() if v > cutoff}

        count = sum(1 for k, v in self._recent_alerts.items()
                    if k.startswith(key.split(":")[0]) and v > cutoff)
        
        if count >= self._rate_limit_max:
            return True
        
        self._recent_alerts[f"{key}:{now}"] = now
        return False

    async def _broadcast(self, alert: dict):
        """Push alert to all subscribed WebSocket clients."""
        for q in self._subscribers[:]:
            try:
                q.put_nowait({"type": "alert", "data": alert})
            except asyncio.QueueFull:
                pass

    async def _send_email(self, alert: dict):
        """Send email notification for critical alerts."""
        if not SMTP_USER or not SMTP_PASSWORD:
            logger.debug("SMTP credentials not set, skipping email")
            return
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[ALERT] {alert['severity'].upper()}: {alert['alert_type']}"
            msg["From"] = SMTP_USER
            msg["To"] = ALERT_EMAIL_TO

            html = f"""
            <html><body>
            <h2 style="color:{'red' if alert['severity']=='critical' else 'orange'}">
                🚨 Security Alert: {alert['alert_type']}
            </h2>
            <table>
                <tr><td><b>Severity:</b></td><td>{alert['severity'].upper()}</td></tr>
                <tr><td><b>Source IP:</b></td><td>{alert['src_ip']}</td></tr>
                <tr><td><b>Destination:</b></td><td>{alert['dst_ip']}</td></tr>
                <tr><td><b>Message:</b></td><td>{alert['message']}</td></tr>
                <tr><td><b>Time:</b></td><td>{time.ctime(alert['timestamp'])}</td></tr>
            </table>
            </body></html>
            """
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_USER, ALERT_EMAIL_TO, msg.as_string())
            
            logger.info(f"Alert email sent to {ALERT_EMAIL_TO}")
        except Exception as e:
            logger.error(f"Email send failed: {e}")
