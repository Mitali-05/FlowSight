# 🛡️ AI-Based Traffic Classification & Monitoring System

> A real-time network traffic analysis system using ML-powered classification, anomaly detection, GeoIP mapping, and a modern multi-page dashboard.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green) ![React](https://img.shields.io/badge/React-18-61DAFB) ![XGBoost](https://img.shields.io/badge/XGBoost-2.0-orange) 

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     NETWORK INTERFACES                          │
│              (eth0, wlan0, lo, en0...)                          │
└────────────────────────┬────────────────────────────────────────┘
                         │  Scapy Packet Capture
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                            │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │Flow Aggreg. │  │ML Classifier │  │ Anomaly Detector     │  │
│  │(5-tuple)    │  │(XGBoost)     │  │ (Isolation Forest)   │  │
│  └─────────────┘  └──────────────┘  └──────────────────────┘  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │GeoIP Lookup │  │Threat Scorer │  │ Alert Engine         │  │
│  │(ip-api.com) │  │(0-100)       │  │ (SMTP + WebSocket)   │  │
│  └─────────────┘  └──────────────┘  └──────────────────────┘  │
│                      asyncio.Queue                              │
│                    SQLite Database                              │
└────────────────────────┬────────────────────────────────────────┘
                         │  WebSocket + REST
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FRONTEND (React)                              │
│  Dashboard │ Live Monitor │ Classification │ Anomalies          │
│  GeoIP Map │ Alerts       │ Reports Export                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
traffic-classifier/
├── backend/
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Configuration settings
│   ├── database.py                # SQLite setup
│   ├── routers/
│   │   ├── capture.py             # Packet capture endpoints
│   │   ├── flows.py               # Flow query endpoints
│   │   ├── alerts.py              # Alert management
│   │   ├── reports.py             # Export endpoints
│   │   └── websocket.py           # WebSocket handler
│   ├── services/
│   │   ├── capture_service.py     # Scapy packet capture
│   │   ├── flow_aggregator.py     # 5-tuple flow builder
│   │   ├── ml_service.py          # ML inference
│   │   ├── anomaly_service.py     # Isolation Forest
│   │   ├── geoip_service.py       # ip-api.com lookup
│   │   ├── threat_service.py      # Threat scoring
│   │   ├── alert_service.py       # Alert triggers + SMTP
│   │   └── fingerprint_service.py # Protocol fingerprinting
│   ├── models/
│   │   ├── flow_model.py          # Pydantic flow schema
│   │   └── alert_model.py         # Alert schema
│   ├── utils/
│   │   ├── feature_extractor.py   # ML feature engineering
│   │   ├── report_generator.py    # CSV/PDF export
│   │   └── helpers.py             # Utility functions
│   └── ml/
│       ├── classifier.pkl          # Trained classifier
│       └── anomaly_detector.pkl    # Trained anomaly model
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/            # Reusable UI components
│   │   ├── pages/                 # 7 dashboard pages
│   │   ├── hooks/                 # Custom React hooks
│   │   └── utils/                 # API + WS utilities
│   ├── package.json
│   └── vite.config.js
├── ml_pipeline/
│   ├── generate_dataset.py        # Synthetic dataset generator
│   ├── train_classifier.py        # XGBoost training
│   ├── train_anomaly.py           # Isolation Forest training
│   └── evaluate_models.py         # Model evaluation
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Root access (for packet capture)

### 1. Clone & Setup

```bash
git clone https://github.com/Mitali-05/FlowSight
cd traffic-classifier
```

### 2. Train ML Models

```bash
cd ml_pipeline
python generate_dataset.py      # Generate synthetic training data
python train_classifier.py      # Train XGBoost classifier
python train_anomaly.py         # Train Isolation Forest
```

### 3. Start Backend

```bash
cd backend
# Must run as root for packet capture
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Start Frontend

```bash
cd frontend
npm run dev
# Open http://localhost:5173
```

---

## ⚙️ Configuration

Edit `backend/config.py`:

```python
CAPTURE_INTERFACE = "eth0"      # Change to your interface
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
ANOMALY_THRESHOLD = -0.1        # Isolation Forest threshold
THREAT_THRESHOLD = 70           # Alert trigger score (0-100)
```

---

## 🎯 Features

| Feature | Status | Description |
|---------|--------|-------------|
| Live Packet Capture | ✅ | Scapy-based, interface selection |
| ML Classification | ✅ | XGBoost, 7 traffic classes |
| Anomaly Detection | ✅ | Isolation Forest, DDoS/port scan |
| Real-Time Dashboard | ✅ | WebSocket, live charts |
| GeoIP Mapping | ✅ | Leaflet.js world map |
| Threat Scoring | ✅ | 0-100 composite score |
| Protocol Fingerprinting | ✅ | Netflix/YouTube/Spotify detection |
| CSV/PDF Export | ✅ | Full session reports |
| Alert System | ✅ | Toast + SMTP email |

---

## 🧠 ML Models

### Traffic Classifier (XGBoost)
- **Classes**: HTTP, DNS, Video Streaming, VoIP, Gaming, Torrent, Unknown
- **Features**: 18 flow-level features (duration, packet count, bytes, port entropy, etc.)
- **Accuracy**: ~94% on synthetic dataset (improves with real data)

### Anomaly Detector (Isolation Forest)
- **Detects**: Port scans, DDoS floods, unusual traffic spikes
- **Score**: -1 (anomaly) to 1 (normal)
- **Contamination**: 5% assumed anomaly rate

### Real Datasets That Can Be Used
- **CICIDS2017**: https://www.unb.ca/cic/datasets/ids-2017.html
- **UNSW-NB15**: https://research.unsw.edu.au/projects/unsw-nb15-dataset
- **CIC-IDS-2018**: https://www.unb.ca/cic/datasets/ids-2018.html

---
