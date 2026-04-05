import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

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
LABEL_COL = "label"


def load_data():
    if not DATASET_PATH.exists():
        print(f"ERROR: Dataset not found at {DATASET_PATH}")
        print("Run:  python generate_dataset.py")
        sys.exit(1)

    print(f"Loading dataset from {DATASET_PATH}...")
    df = pd.read_csv(DATASET_PATH)
    print(f"  Loaded {len(df):,} rows, {df[LABEL_COL].nunique()} classes")
    print(f"  Class distribution:\n{df[LABEL_COL].value_counts().to_string()}\n")
    return df


def preprocess(df):
    """Clean, encode, and split data."""
    # Drop nulls
    df = df.dropna(subset=FEATURE_COLS + [LABEL_COL])

    # Clip extreme outliers (99.9th percentile)
    for col in ["byte_count", "packet_count", "bytes_per_second", "packets_per_second"]:
        cap = df[col].quantile(0.999)
        df[col] = df[col].clip(upper=cap)

    X = df[FEATURE_COLS].values.astype(np.float32)
    y_raw = df[LABEL_COL].values

    # Encode labels
    le = LabelEncoder()
    y = le.fit_transform(y_raw)
    print(f"Label mapping: {dict(zip(le.classes_, le.transform(le.classes_)))}\n")

    return X, y, le


def train(X_train, y_train, X_val, y_val):
    """Train XGBoost with cross-validation."""
    print("Training XGBoost classifier...")

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=8,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        reg_alpha=0.1,
        reg_lambda=1.0,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
        early_stopping_rounds=20,
        verbosity=1,
    )

    t0 = time.time()
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=50,
    )
    elapsed = time.time() - t0
    print(f"\nTraining complete in {elapsed:.1f}s")
    print(f"Best iteration: {model.best_iteration}")
    return model


def evaluate(model, X_test, y_test, le):
    """Print full evaluation metrics."""
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n{'='*60}")
    print(f"Test Accuracy: {acc:.4f} ({acc*100:.2f}%)")
    print(f"{'='*60}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=le.classes_))
    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(pd.DataFrame(cm, index=le.classes_, columns=le.classes_).to_string())
    return acc


def feature_importance(model, top_n=10):
    """Print top N most important features."""
    importances = model.feature_importances_
    ranked = sorted(zip(FEATURE_COLS, importances), key=lambda x: -x[1])
    print(f"\nTop {top_n} Feature Importances:")
    for feat, imp in ranked[:top_n]:
        bar = "█" * int(imp * 50)
        print(f"  {feat:<25} {imp:.4f}  {bar}")


def save_models(model, le):
    clf_path = OUTPUT_DIR / "classifier.pkl"
    le_path  = OUTPUT_DIR / "label_encoder.pkl"
    with open(clf_path, "wb") as f:
        pickle.dump(model, f, protocol=pickle.HIGHEST_PROTOCOL)
    with open(le_path, "wb") as f:
        pickle.dump(le, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"\n✅ Classifier saved to: {clf_path}")
    print(f"✅ Label encoder saved to: {le_path}")


def main():
    df = load_data()
    X, y, le = preprocess(df)

    # Stratified split: 70% train, 15% val, 15% test
    X_tmp, X_test, y_tmp, y_test = train_test_split(
        X, y, test_size=0.15, stratify=y, random_state=42
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_tmp, y_tmp, test_size=0.176, stratify=y_tmp, random_state=42
    )  # 0.176 of 85% ≈ 15% overall

    print(f"Train: {len(X_train):,} | Val: {len(X_val):,} | Test: {len(X_test):,}")

    model = train(X_train, y_train, X_val, y_val)
    acc = evaluate(model, X_test, y_test, le)
    feature_importance(model)
    save_models(model, le)

    print(f"\n🎯 Final Test Accuracy: {acc*100:.2f}%")
    print("Models ready for inference in backend/ml/")


if __name__ == "__main__":
    main()
