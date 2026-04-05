import pickle
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    roc_auc_score, precision_recall_curve, average_precision_score,
)
from sklearn.model_selection import cross_val_score

DATASET_PATH = Path(__file__).parent / "dataset.csv"
MODEL_DIR = Path(__file__).parent.parent / "backend" / "ml"

FEATURE_COLS = [
    "duration", "packet_count", "byte_count", "avg_pkt_size",
    "max_pkt_size", "min_pkt_size", "inter_arrival",
    "bytes_per_second", "packets_per_second",
    "src_port", "dst_port",
    "is_tcp", "is_udp", "is_icmp",
    "port_entropy", "pkt_size_variance", "large_pkt_ratio", "small_pkt_ratio",
]


def load_models():
    clf_path = MODEL_DIR / "classifier.pkl"
    le_path  = MODEL_DIR / "label_encoder.pkl"
    anom_path = MODEL_DIR / "anomaly_detector.pkl"

    models = {}
    for name, path in [("classifier", clf_path), ("label_encoder", le_path), ("anomaly", anom_path)]:
        if path.exists():
            with open(path, "rb") as f:
                models[name] = pickle.load(f)
            print(f"✅ Loaded {name} from {path}")
        else:
            print(f"❌ {name} not found at {path}")
    return models


def evaluate_classifier(model, le, df):
    print("\n" + "="*60)
    print("CLASSIFIER EVALUATION")
    print("="*60)

    X = df[FEATURE_COLS].values.astype(np.float32)
    y = le.transform(df["label"].values)

    y_pred = model.predict(X)
    acc = accuracy_score(y, y_pred)

    print(f"\nOverall Accuracy: {acc*100:.2f}%")
    print("\nPer-class Report:")
    print(classification_report(y, y_pred, target_names=le.classes_))

    print("\nConfusion Matrix:")
    cm = confusion_matrix(y, y_pred)
    cm_df = pd.DataFrame(cm, index=le.classes_, columns=le.classes_)
    print(cm_df.to_string())

    # Top misclassifications
    print("\nTop Misclassification Pairs:")
    errors = []
    for i, true_label in enumerate(le.classes_):
        for j, pred_label in enumerate(le.classes_):
            if i != j and cm[i, j] > 0:
                errors.append((cm[i, j], true_label, pred_label))
    errors.sort(reverse=True)
    for count, true_l, pred_l in errors[:5]:
        print(f"  {true_l} → {pred_l}: {count} times")

    # Feature importances
    if hasattr(model, "feature_importances_"):
        print("\nFeature Importances (top 10):")
        ranked = sorted(zip(FEATURE_COLS, model.feature_importances_), key=lambda x: -x[1])
        for feat, imp in ranked[:10]:
            bar = "█" * int(imp * 60)
            print(f"  {feat:<25} {imp:.4f}  {bar}")

    return acc


def evaluate_anomaly(model, df):
    print("\n" + "="*60)
    print("ANOMALY DETECTOR EVALUATION")
    print("="*60)

    # Evaluate on normal flows
    normal_df = df[df["label"].isin(["HTTP", "DNS", "Video_Streaming", "VoIP", "Gaming"])]
    X_normal = normal_df[FEATURE_COLS].values.astype(np.float32)

    scores_normal = model.decision_function(X_normal)
    preds_normal = model.predict(X_normal)

    # Count false positives (normal labeled as anomaly)
    fp = (preds_normal == -1).sum()
    fp_rate = fp / len(preds_normal)

    print(f"\nNormal traffic evaluation ({len(X_normal):,} flows):")
    print(f"  False Positive Rate: {fp_rate*100:.2f}% ({fp} flows flagged incorrectly)")
    print(f"  Mean decision score: {scores_normal.mean():.4f}")
    print(f"  Score distribution (percentiles):")
    for pct in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
        val = np.percentile(scores_normal, pct)
        print(f"    {pct:3d}th: {val:.4f}")

    print(f"\nRecommended thresholds:")
    print(f"  Conservative (1% FP): {np.percentile(scores_normal, 1):.4f}")
    print(f"  Balanced   (5% FP): {np.percentile(scores_normal, 5):.4f}")
    print(f"  Aggressive (10% FP): {np.percentile(scores_normal, 10):.4f}")


def main():
    if not DATASET_PATH.exists():
        print("ERROR: Run generate_dataset.py first")
        sys.exit(1)

    print("Loading dataset...")
    df = pd.read_csv(DATASET_PATH)
    df = df.sample(n=min(10000, len(df)), random_state=42)
    print(f"Loaded {len(df):,} samples for evaluation\n")

    models = load_models()
    if not models:
        print("No models found. Run train_classifier.py and train_anomaly.py first.")
        sys.exit(1)

    if "classifier" in models and "label_encoder" in models:
        # Filter to only labeled flows the encoder knows about
        known_labels = list(models["label_encoder"].classes_)
        eval_df = df[df["label"].isin(known_labels)]
        if len(eval_df) > 0:
            evaluate_classifier(models["classifier"], models["label_encoder"], eval_df)

    if "anomaly" in models:
        evaluate_anomaly(models["anomaly"], df)

    print("\n" + "="*60)
    print("Evaluation complete.")


if __name__ == "__main__":
    main()
