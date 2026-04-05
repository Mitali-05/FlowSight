import pickle
import time
import random
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

DATASET_PATH = Path(__file__).parent / "dataset.csv"
OUTPUT_DIR   = Path(__file__).parent.parent / "backend" / "ml"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "duration", "packet_count", "byte_count", "avg_pkt_size",
    "max_pkt_size", "min_pkt_size", "inter_arrival",
    "bytes_per_second", "packets_per_second",
    "src_port", "dst_port",
    "is_tcp", "is_udp", "is_icmp",
    "port_entropy", "pkt_size_variance", "large_pkt_ratio", "small_pkt_ratio",
]

# Contamination: expected fraction of anomalies in real traffic
CONTAMINATION = 0.05  # 5%


def generate_anomalies(n: int = 2500) -> pd.DataFrame:
    rows = []
    random.seed(99)
    np.random.seed(99)

    for _ in range(n // 4):
        # Port scan
        rows.append({
            "duration": np.random.uniform(0.01, 2.0),
            "packet_count": np.random.randint(50, 500),
            "byte_count": np.random.randint(50, 5000),
            "avg_pkt_size": np.random.uniform(40, 80),
            "max_pkt_size": np.random.randint(64, 128),
            "min_pkt_size": 40,
            "inter_arrival": np.random.uniform(0.001, 0.01),
            "bytes_per_second": np.random.uniform(100, 5000),
            "packets_per_second": np.random.uniform(50, 500),
            "src_port": 12345,
            "dst_port": np.random.randint(1, 65535),
            "is_tcp": 1, "is_udp": 0, "is_icmp": 0,
            "port_entropy": 0.95,
            "pkt_size_variance": 0.1,
            "large_pkt_ratio": 0.0,
            "small_pkt_ratio": 1.0,
            "label": "anomaly",
        })

    for _ in range(n // 4):

        rows.append({
            "duration": np.random.uniform(0.1, 5.0),
            "packet_count": np.random.randint(5000, 100000),
            "byte_count": np.random.randint(300000, 10000000),
            "avg_pkt_size": np.random.uniform(64, 128),
            "max_pkt_size": 128,
            "min_pkt_size": 64,
            "inter_arrival": np.random.uniform(0.0001, 0.001),
            "bytes_per_second": np.random.uniform(1e6, 1e8),
            "packets_per_second": np.random.uniform(1000, 50000),
            "src_port": np.random.randint(1024, 65535),
            "dst_port": 80,
            "is_tcp": 0, "is_udp": 1, "is_icmp": 0,
            "port_entropy": 0.6,
            "pkt_size_variance": 0.05,
            "large_pkt_ratio": 0.0,
            "small_pkt_ratio": 0.9,
            "label": "anomaly",
        })

    for _ in range(n // 4):
        rows.append({
            "duration": np.random.uniform(60, 3600),
            "packet_count": np.random.randint(10, 50),
            "byte_count": np.random.randint(500, 5000),
            "avg_pkt_size": np.random.uniform(100, 200),
            "max_pkt_size": 250,
            "min_pkt_size": 80,
            "inter_arrival": np.random.uniform(29.9, 30.1),   # ~30s beacon
            "bytes_per_second": np.random.uniform(1, 10),
            "packets_per_second": np.random.uniform(0.01, 0.05),
            "src_port": np.random.randint(1024, 65535),
            "dst_port": np.random.randint(50000, 65535),
            "is_tcp": 1, "is_udp": 0, "is_icmp": 0,
            "port_entropy": 0.9,
            "pkt_size_variance": 0.05,
            "large_pkt_ratio": 0.0,
            "small_pkt_ratio": 0.5,
            "label": "anomaly",
        })

    for _ in range(n // 4):
        rows.append({
            "duration": np.random.uniform(10, 300),
            "packet_count": np.random.randint(1000, 50000),
            "byte_count": np.random.randint(10_000_000, 500_000_000),
            "avg_pkt_size": np.random.uniform(1200, 1450),
            "max_pkt_size": 1500,
            "min_pkt_size": 800,
            "inter_arrival": np.random.uniform(0.01, 0.1),
            "bytes_per_second": np.random.uniform(100000, 5000000),
            "packets_per_second": np.random.uniform(10, 500),
            "src_port": np.random.randint(1024, 65535),
            "dst_port": np.random.choice([4444, 31337, 65535, 8888]),
            "is_tcp": 1, "is_udp": 0, "is_icmp": 0,
            "port_entropy": 0.85,
            "pkt_size_variance": 0.1,
            "large_pkt_ratio": 1.0,
            "small_pkt_ratio": 0.0,
            "label": "anomaly",
        })

    return pd.DataFrame(rows)


def main():
    print("Loading normal traffic from dataset...")
    if DATASET_PATH.exists():
        df_normal = pd.read_csv(DATASET_PATH)
        normal_labels = ["HTTP", "DNS", "Video_Streaming", "VoIP", "Gaming"]
        df_normal = df_normal[df_normal["label"].isin(normal_labels)]
        df_normal = df_normal.sample(n=min(20000, len(df_normal)), random_state=42)
        print(f"  Normal flows: {len(df_normal):,}")
    else:
        print("  Dataset not found, generating synthetic normals...")
        from generate_dataset import generate_flow, CLASSES
        rows = []
        for label in ["HTTP", "DNS", "Video_Streaming", "VoIP", "Gaming"]:
            for _ in range(4000):
                flow = generate_flow(label, CLASSES[label])
                flow["label"] = label
                rows.append(flow)
        df_normal = pd.DataFrame(rows)

    print("Generating anomalous flows...")
    df_anomaly = generate_anomalies(2500)
    print(f"  Anomalous flows: {len(df_anomaly):,}")

    df_all = pd.concat([df_normal, df_anomaly], ignore_index=True)
    X = df_all[FEATURE_COLS].values.astype(np.float32)
    y_true = (df_all["label"] == "anomaly").astype(int).values

    for i, col in enumerate(FEATURE_COLS):
        cap = np.percentile(X[:, i], 99.9)
        X[:, i] = np.clip(X[:, i], 0, cap)

    print(f"\nTraining Isolation Forest (contamination={CONTAMINATION})...")
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("iso", IsolationForest(
            n_estimators=200,
            max_samples="auto",
            contamination=CONTAMINATION,
            max_features=1.0,
            bootstrap=False,
            random_state=42,
            n_jobs=-1,
            verbose=1,
        )),
    ])

    t0 = time.time()
    X_normal = X[y_true == 0]
    pipeline.fit(X_normal)
    elapsed = time.time() - t0
    print(f"Training complete in {elapsed:.1f}s")

    print("\nEvaluating on combined normal + anomaly data...")
    scores = pipeline.decision_function(X)
    preds_raw = pipeline.predict(X)

    # Isolation Forest returns -1 (anomaly) or 1 (normal)
    preds_binary = (preds_raw == -1).astype(int)

    print("\nClassification Report (1=anomaly, 0=normal):")
    print(classification_report(y_true, preds_binary, target_names=["normal", "anomaly"]))

    try:
        auc = roc_auc_score(y_true, -scores)
        print(f"ROC-AUC Score: {auc:.4f}")
    except Exception:
        pass

    normal_scores = scores[y_true == 0]
    anom_scores = scores[y_true == 1]
    print(f"\nDecision Function Scores:")
    print(f"  Normal   — mean: {normal_scores.mean():.3f}, std: {normal_scores.std():.3f}")
    print(f"  Anomaly  — mean: {anom_scores.mean():.3f}, std: {anom_scores.std():.3f}")
    print(f"  Suggested threshold: {np.percentile(normal_scores, 5):.3f}")

    out_path = OUTPUT_DIR / "anomaly_detector.pkl"
    with open(out_path, "wb") as f:
        pickle.dump(pipeline, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"\n✅ Anomaly detector saved to: {out_path}")
    print("Update ANOMALY_THRESHOLD in config.py based on suggested threshold above.")


if __name__ == "__main__":
    main()
