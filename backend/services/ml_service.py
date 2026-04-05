import pickle
import logging
import numpy as np
from pathlib import Path
from typing import Optional

from config import CLASSIFIER_PATH, LABEL_ENCODER_PATH, TRAFFIC_CLASSES
from utils.feature_extractor import extract_features

logger = logging.getLogger(__name__)


class MLClassifierService:
    """
    Loads a pre-trained XGBoost classifier and performs inference
    on completed flow records.
    """

    def __init__(self):
        self.model = None
        self.label_encoder = None
        self._loaded = False

    def load(self):
        """Load model and label encoder from disk."""
        try:
            if CLASSIFIER_PATH.exists():
                with open(CLASSIFIER_PATH, "rb") as f:
                    self.model = pickle.load(f)
                logger.info(f"Loaded classifier from {CLASSIFIER_PATH}")
            else:
                logger.warning(f"Classifier not found at {CLASSIFIER_PATH} — using rule-based fallback")

            if LABEL_ENCODER_PATH.exists():
                with open(LABEL_ENCODER_PATH, "rb") as f:
                    self.label_encoder = pickle.load(f)
            
            self._loaded = True
        except Exception as e:
            logger.error(f"Failed to load classifier: {e}")
            self._loaded = False

    def classify(self, flow: dict) -> str:
        """
        Classify a flow dict into a traffic category.
        Falls back to rule-based classification if model not loaded.
        
        Returns: traffic class label (e.g., "HTTP", "Video_Streaming")
        """
        if self.model is not None:
            return self._ml_classify(flow)
        else:
            return self._rule_classify(flow)

    def classify_batch(self, flows: list[dict]) -> list[str]:
        """Classify a batch of flows at once (more efficient)."""
        if self.model is not None:
            try:
                features = np.vstack([extract_features(f) for f in flows])
                preds = self.model.predict(features)
                if self.label_encoder is not None:
                    return self.label_encoder.inverse_transform(preds).tolist()
                return [TRAFFIC_CLASSES[p] if p < len(TRAFFIC_CLASSES) else "Unknown"
                        for p in preds]
            except Exception as e:
                logger.error(f"Batch classify error: {e}")
        return [self._rule_classify(f) for f in flows]

    def _ml_classify(self, flow: dict) -> str:
        """ML-based classification."""
        try:
            features = extract_features(flow)
            pred = self.model.predict(features)[0]
            if self.label_encoder is not None:
                return self.label_encoder.inverse_transform([pred])[0]
            if isinstance(pred, (int, np.integer)) and pred < len(TRAFFIC_CLASSES):
                return TRAFFIC_CLASSES[pred]
            return str(pred)
        except Exception as e:
            logger.debug(f"ML classify error: {e}")
            return self._rule_classify(flow)

    def _rule_classify(self, flow: dict) -> str:
        """
        Rule-based fallback classifier using ports and protocol heuristics.
        Used when model is not available or as a sanity check.
        """
        dst_port = flow.get("dst_port", 0)
        src_port = flow.get("src_port", 0)
        protocol = flow.get("protocol", "").upper()
        byte_count = flow.get("byte_count", 0)
        avg_pkt_size = flow.get("avg_pkt_size", 0)
        duration = flow.get("duration", 0)

        # DNS
        if protocol == "DNS" or dst_port == 53 or src_port == 53:
            return "DNS"

        # VoIP
        if dst_port in {5060, 5061, 5004, 5005} or src_port in {5060, 5061}:
            return "VoIP"
        if protocol == "UDP" and avg_pkt_size < 300 and flow.get("packet_count", 0) > 20:
            return "VoIP"

        # Gaming
        if protocol == "UDP" and dst_port in {3074, 3478, 3479, 27015, 27016, 7777}:
            return "Gaming"

        # Torrent
        if dst_port in range(6881, 6890) or src_port in range(6881, 6890):
            return "Torrent"
        if dst_port == 51413 or src_port == 51413:
            return "Torrent"

        # Video Streaming
        if dst_port in {443, 80} and byte_count > 500_000 and avg_pkt_size > 800:
            return "Video_Streaming"

        # HTTP/HTTPS
        if dst_port in {80, 443, 8080, 8443}:
            return "HTTP"

        # SSH
        if dst_port == 22 or src_port == 22:
            return "Unknown"

        return "Unknown"

    def get_confidence(self, flow: dict) -> float:
        """Return prediction confidence (0-1) if model supports it."""
        if self.model is not None:
            try:
                features = extract_features(flow)
                proba = self.model.predict_proba(features)[0]
                return float(np.max(proba))
            except Exception:
                pass
        return 1.0  # Rule-based is "certain"
