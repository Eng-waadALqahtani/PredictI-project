import os
import pickle
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import numpy as np
from sklearn.ensemble import IsolationForest

from models import Event, ThreatFingerprint
from storage import EVENTS_STORE, store_fingerprint, FINGERPRINTS_STORE

# Path to the pre-trained Isolation Forest model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "models", "isoforest_absher.pkl")

# Global variable to store the loaded model
_isolation_forest_model: Optional[IsolationForest] = None

# Reference values for risk score conversion (Adjusted for better sensitivity)
MAX_NORMAL_SCORE = 0.1
MIN_ANOMALY_SCORE = -0.25 # Adjusted for better detection


def load_model() -> IsolationForest:
    """Load the pre-trained Isolation Forest model."""
    global _isolation_forest_model
    
    if _isolation_forest_model is not None:
        return _isolation_forest_model
    
    try:
        # Load the model from the file path
        with open(MODEL_PATH, 'rb') as f:
            _isolation_forest_model = pickle.load(f)
        print("✅ [PREDICTAI] ML Model loaded successfully from disk.")
    except FileNotFoundError:
        # Create a dummy model if file is missing (for demo purposes)
        print("⚠️ [PREDICTAI] Model file not found. Initializing dummy model.")
        _isolation_forest_model = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_estimators=100
        )
        dummy_data = np.random.rand(100, 4) # Ensure it supports 4 features for the calculation
        _isolation_forest_model.fit(dummy_data)
        
    return _isolation_forest_model


def calculate_behavioral_features(user_id: str, device_id: str, current_time: datetime) -> Dict[str, Any]:
    """
    Aggregate events for the last 10 minutes and calculate behavioral features.
    Uses OR logic: matches events if EITHER user_id OR device_id matches.
    This ensures detection works even when device changes.
    """
    time_window_start = current_time - timedelta(minutes=10)
    
    recent_events = [
        event for event in EVENTS_STORE
        if (event.user_id == user_id or event.device_id == device_id)
        and event.timestamp1 >= time_window_start
    ]
    
    # --- 1. Basic Feature Calculation ---
    total_events = len(recent_events)
    update_mobile_attempts = sum(
        1 for event in recent_events
        if event.event_type == "update_mobile_attempt"
    )
    
    time_span_minutes = 10.0
    if total_events > 0:
        earliest_event = min(event.timestamp1 for event in recent_events)
        actual_span = (current_time - earliest_event).total_seconds() / 60.0
        time_span_minutes = max(actual_span, 1.0)
    
    events_per_minute = total_events / time_span_minutes
    
    # --- 2. Unusual Navigation Feature (pages_visited_count) ---
    unique_services = set()
    for event in recent_events:
        event_type = event.event_type
        
        # Logic to extract unique service identifiers (based on the frontend payload)
        if event_type.startswith("view_service_"):
            service_name = event_type.replace("view_service_", "", 1)
            if service_name:
                unique_services.add(service_name)
        elif "view" in event_type.lower() or "login" in event_type.lower():
            unique_services.add(event_type)

    pages_visited_count = len(unique_services)
    
    features = {
        "total_events": total_events,
        "update_mobile_attempt_count": update_mobile_attempts,
        "events_per_minute": events_per_minute,
        "pages_visited_count": pages_visited_count
    }
    
    return features


def get_risk_score(raw_score: float) -> int:
    """
    Convert Isolation Forest decision function score to Risk Score (0-100).
    """
    normalized = (raw_score - MIN_ANOMALY_SCORE) / (MAX_NORMAL_SCORE - MIN_ANOMALY_SCORE)
    risk_score = 100 * (1.0 - normalized)
    risk_score = max(0, min(100, int(risk_score)))
    
    return risk_score


def is_user_fingerprinted(user_id: str) -> bool:
    """
    Check if a user has an ACTIVE high-risk threat fingerprint registered.
    """
    for fingerprint in FINGERPRINTS_STORE:
        # Check if this fingerprint belongs to the user, has high risk (>= 80), and is ACTIVE
        if (fingerprint.user_id == user_id and 
            fingerprint.risk_score >= 80 and 
            fingerprint.status == "ACTIVE"):
            return True
    
    return False


def process_event(event: Event) -> Optional[ThreatFingerprint]:
    """
    Process an event through the Threat Engine to detect anomalies.
    - Uses IsolationForest on 3 features only (model was trained on 3).
    - Adds rule-based fallback so we still create fingerprints even if the model fails.
    """
    # 1) حساب الخصائص السلوكية من آخر 10 دقائق
    behavioral_features = calculate_behavioral_features(
        event.user_id,
        event.device_id,
        event.timestamp1
    )

    # اطبعها للتشخيص
    print(f"🧠 [FEATURES] user={event.user_id[:8]} dev={event.device_id[:8]} → {behavioral_features}")

    # 2) تجهيز نموذج العزل
    model = None
    try:
        model = load_model()
    except Exception as e:
        print(f"⚠️ [WARN] Failed to load IsolationForest model: {e}")

    risk_score = 0
    ml_used = False

    # 3) تشغيل الـ ML على 3 خصائص فقط (كما تم تدريب النموذج)
    if model is not None:
        try:
            # اختر 3 خصائص للـ model (يمكن تعديل الاختيار لو أردتِ)
            x_total = behavioral_features.get("total_events", 0.0)
            x_updates = behavioral_features.get("update_mobile_attempt_count", 0.0)
            x_rate = behavioral_features.get("events_per_minute", 0.0)
            # يمكنك مثلاً استخدام pages_visited_count بدل rate:
            # x_pages = behavioral_features.get("pages_visited_count", 0.0)

            feature_vector = np.array([[x_total, x_updates, x_rate]])
            raw_score = model.decision_function(feature_vector)[0]
            risk_score = get_risk_score(raw_score)
            ml_used = True
            print(f"🤖 [ML] raw_score={raw_score:.4f} → risk_score={risk_score}")
        except Exception as e:
            # هنا الخطأ الذي كان يظهر: X has 4 features ...
            print(f"⚠️ [WARN] ML prediction failed, fallback to rules only: {e}")
            risk_score = 0
            ml_used = False

    # 4) قواعد fallback على السلوك (حتى لو ML فشل)
    total_events = behavioral_features.get("total_events", 0)
    update_attempts = behavioral_features.get("update_mobile_attempt_count", 0)
    events_per_minute = behavioral_features.get("events_per_minute", 0.0)
    pages_visited = behavioral_features.get("pages_visited_count", 0)

    # حدود تقريبية للهجوم (تقدرين تعدلينها)
    is_fast_drain = total_events >= 20 and events_per_minute >= 5.0
    is_high_rate = events_per_minute >= 8.0
    is_multiple_updates = update_attempts >= 3
    is_unusual_navigation = pages_visited >= 6
    is_high_volume = total_events >= 30

    should_create_fingerprint = False
    trigger_source = "NONE"

    # 5) قرار إنشاء بصمة
    # أولاً: اعتماداً على الـ ML لو عطى Risk عالي
    if ml_used and risk_score >= 80:
        should_create_fingerprint = True
        trigger_source = "ML_HIGH_RISK"

    # ثانياً: قواعد fallback
    if not should_create_fingerprint:
        if (is_fast_drain or is_high_rate or
            is_multiple_updates or is_unusual_navigation or
            is_high_volume):
            should_create_fingerprint = True
            trigger_source = "RULES_FALLBACK"
            # إذا الـ ML عطى درجة أقل، نضمن أنها عالية بما يكفي للحجب
            if risk_score < 80:
                risk_score = max(risk_score, 85)

    print(
        f"🔍 [EVAL] src={trigger_source} | "
        f"risk={risk_score} | "
        f"fast_drain={is_fast_drain}, high_rate={is_high_rate}, "
        f"multi_updates={is_multiple_updates}, nav={is_unusual_navigation}, "
        f"high_volume={is_high_volume}"
    )

    # 6) إنشاء وحفظ البصمة إن لزم
    if should_create_fingerprint:
        # Add platform, IP, and user agent to behavioral features for dashboard display
        behavioral_features["platform"] = getattr(event, "platform", None)
        behavioral_features["ip_address"] = getattr(event, "ip_address", None)
        behavioral_features["user_agent"] = getattr(event, "user_agent", None)
        
        fingerprint = ThreatFingerprint(
            fingerprint_id=f"fp-{uuid.uuid4().hex[:12]}",
            risk_score=risk_score,
            user_id=event.user_id,
            status="ACTIVE",
            behavioral_features=behavioral_features,
            device_id=event.device_id,
            ip_address=getattr(event, "ip_address", None),
            user_agent=getattr(event, "user_agent", None)
        )
        store_fingerprint(fingerprint)
        print(f"   ✅ Fingerprint created: {fingerprint.fingerprint_id} (Blocking Activated)")
        print(f"      User: {event.user_id}, Device: {event.device_id}, IP: {getattr(event, 'ip_address', 'N/A')}")
        return fingerprint

    return None
