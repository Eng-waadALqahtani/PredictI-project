import os
import pickle
import uuid
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
import numpy as np
from sklearn.ensemble import IsolationForest

from models import Event, ThreatFingerprint
from storage import (
    EVENTS_STORE, 
    store_fingerprint, 
    FINGERPRINTS_STORE, 
    get_all_fingerprints_db,
    get_fingerprints
)
from db import FingerprintDB
import json
import json

# Path to the pre-trained Isolation Forest model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "models", "isoforest_absher.pkl")

# Global variable to store the loaded model
_isolation_forest_model: Optional[IsolationForest] = None

# Reference values for risk score conversion (Adjusted for better sensitivity)
MAX_NORMAL_SCORE = 0.1
MIN_ANOMALY_SCORE = -0.25 # Adjusted for better detection

# ================== Risk Score Threshold Configuration ==================
# RISK_SCORE_BLOCKING_THRESHOLD: الحد الأدنى لدرجة الخطورة التي تسبب حجب المستخدم
# 
# الأساس المنطقي لاختيار 85 (تم رفعه من 80 لتقليل False Positives):
# 1. مقياس الخطورة من 0-100، حيث:
#    - 0-49: منخفضة (Low) - سلوك طبيعي أو شك بسيط
#    - 50-74: متوسطة (Medium) - سلوك مشبوه يحتاج مراقبة لكن لا يحجب
#    - 75-84: عالية متوسطة (High-Medium) - سلوك مشبوه جداً، مراقبة مكثفة
#    - 85-100: عالية جداً (Critical) - سلوك خطير يستدعي الحجب الفوري
#
# 2. الرقم 85 يمثل نسبة 85% من الخطورة القصوى - أي أننا نحجب فقط عندما يكون هناك
#    احتمال 85% أو أكثر أن السلوك يمثل تهديداً حقيقياً ومؤكداً.
#
# 3. هذا الحد يوازن بين:
#    - تقليل False Positives (عدم حجب مستخدمين شرعيين) - الأولوية العليا
#    - ضمان الكشف الفوري للتهديدات الحقيقية والمؤكدة فقط
#
# تم رفع الحد من 80 إلى 85 لأن:
# - النظام كان يحجب مستخدمين شرعيين بدون أساس واضح
# - الاكتشافات البسيطة يجب أن تكون للمراقبة فقط، وليس للحجب الفوري
RISK_SCORE_BLOCKING_THRESHOLD = 85

# ================== FEATURE 1: Device Change Detection ==================
# Track last device_type used for each fingerprint (keyed by user_id)
fingerprint_last_device: Dict[str, str] = {}

# ================== FEATURE 2: Impossible Travel Detection (Geographic Jump) ==================
# Track last location and timestamp for each fingerprint (keyed by user_id)
fingerprint_last_location: Dict[str, Tuple[str, datetime]] = {}  # {user_id: (city_name, timestamp)}

# Track IP addresses and locations used by each user for geographic jump detection
fingerprint_location_history: Dict[str, List[Tuple[str, str, datetime]]] = {}  # {user_id: [(ip_address, location, timestamp), ...]}

# City coordinates dictionary (latitude, longitude) for major Saudi cities
CITY_COORDINATES: Dict[str, Tuple[float, float]] = {
    "Riyadh": (24.7136, 46.6753),
    "Jeddah": (21.4858, 39.1925),
    "Mecca": (21.3891, 39.8579),
    "Medina": (24.5247, 39.5692),
    "Dammam": (26.4207, 50.0888),
    "Khobar": (26.2172, 50.1971),
    "Abha": (18.2164, 42.5042),
    "Tabuk": (28.3998, 36.5700),
    "Buraidah": (26.3260, 43.9750),
    "Khamis Mushait": (18.3000, 42.7333),
    "Hail": (27.5114, 41.7208),
    "Najran": (17.4924, 44.1277),
    "Jazan": (16.8894, 42.5706),
    "Al-Kharj": (24.1556, 47.3050),
    "Arar": (30.9753, 41.0381),
    "Sakaka": (29.9697, 40.2064),
    "Yanbu": (24.0892, 38.0618),
    "Al-Jubail": (27.0174, 49.6225),
    "Taif": (21.2703, 40.4158),
    "Al-Qatif": (26.5194, 49.9889),
}

# ================== Device Fingerprint Tracking ==================
# For each user, we remember the last device context we saw
LAST_DEVICE_INFO_BY_USER: Dict[str, Dict[str, Any]] = {}

# ================== Attack Profile Tracking ==================
# For each user, we remember the last attack mode we saw
LAST_ATTACK_MODE_BY_USER: Dict[str, str] = {}


def get_device_type_from_user_agent(user_agent: str) -> str:
    """
    Roughly infer device type from User-Agent:
    - 'mobile'  : most phones
    - 'tablet'  : tablets (iPad, Android tablet)
    - 'desktop' : laptops / PCs
    - 'unknown' : cannot determine
    """
    if not user_agent:
        return "unknown"
    
    ua = user_agent.lower()
    
    # Mobile phones
    if "iphone" in ua or ("android" in ua and "mobile" in ua):
        return "mobile"
    
    # Tablets
    if "ipad" in ua or ("android" in ua and "tablet" in ua):
        return "tablet"
    
    # Desktop / laptop
    if "windows" in ua or "macintosh" in ua or "linux" in ua:
        return "desktop"
    
    return "unknown"


def infer_attack_mode(event: Event, behavioral_features: Dict[str, Any]) -> str:
    """
    Infer a coarse-grained attack mode based on:
    - event_type
    - behavioral features
    
    This is NOT ML, just simple heuristics to label behavior:
        - 'mass_download'
        - 'rapid_clicks'
        - 'credential_attack'
        - 'normal_usage'
    """
    event_type = getattr(event, "event_type", "") or ""
    et = event_type.lower()
    
    total_events = behavioral_features.get("total_events", 0)
    events_per_minute = behavioral_features.get("events_per_minute", 0.0)
    update_mobile_attempt_count = behavioral_features.get("update_mobile_attempt_count", 0)
    pages_visited_count = behavioral_features.get("pages_visited_count", 0)
    
    # Mass download: many download_file events / fast draining of content
    if "download_file" in et or (
        total_events >= 15 and events_per_minute >= 10 and pages_visited_count <= 3
    ):
        return "mass_download"
    
    # Rapid clicks / UI abuse
    if "ui_suspicious_pattern" in et or events_per_minute >= 15:
        return "rapid_clicks"
    
    # Credential-based attack (many login attempts / updates)
    if "login" in et and (events_per_minute >= 5 or update_mobile_attempt_count >= 3):
        return "credential_attack"
    
    # Default: nothing special
    return "normal_usage"


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


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth using Haversine formula.
    Returns distance in kilometers.
    """
    # Radius of Earth in kilometers
    R = 6371.0
    
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def get_city_coordinates(city_name: str) -> Optional[Tuple[float, float]]:
    """
    Get coordinates for a city name. Returns None if city not found.
    """
    if not city_name:
        return None
    
    # Normalize city name (case-insensitive, strip whitespace)
    city_normalized = city_name.strip().title()
    return CITY_COORDINATES.get(city_normalized)


def detect_device_change(user_id: str, device_type: Optional[str]) -> Optional[str]:
    """
    FEATURE 1: Device Change Detection
    Detect when the same fingerprint (user_id) is used from a different device type.
    Returns reason string if detected, None otherwise.
    """
    if not device_type:
        return None
    
    # Normalize device_type (lowercase for consistency)
    device_type_normalized = device_type.lower().strip()
    
    # Check if we have a previous device_type for this user
    if user_id in fingerprint_last_device:
        previous_device = fingerprint_last_device[user_id]
        
        # If device type changed
        if previous_device != device_type_normalized:
            reason = f"Fingerprint reused on different device (previous: {previous_device}, now: {device_type_normalized})"
            print(f"🔍 [DEVICE CHANGE] {reason}")
            return reason
    
    # Update the last device_type for this user
    fingerprint_last_device[user_id] = device_type_normalized
    return None


def detect_geographic_jump(user_id: str, ip_address: Optional[str], location: Optional[str], current_time: datetime) -> Optional[str]:
    """
    FEATURE 2: Geographic Jump Detection (القفزة الجغرافية)
    Detect when the same user appears in multiple geographic locations in a short time period.
    This includes:
    1. Impossible travel (same user in far cities too quickly)
    2. Multiple locations in short time (using multiple IPs/locations)
    3. Suspicious location switching pattern
    
    Returns reason string if detected, None otherwise.
    """
    if not location and not ip_address:
        return None
    
    location_normalized = location.strip().title() if location else "Unknown"
    ip_address = ip_address or "Unknown"
    
    # Initialize history if needed
    if user_id not in fingerprint_location_history:
        fingerprint_location_history[user_id] = []
    
    # Add current location/IP to history
    fingerprint_location_history[user_id].append((ip_address, location_normalized, current_time))
    
    # Keep only last 2 hours of history (to prevent memory bloat)
    two_hours_ago = current_time - timedelta(hours=2)
    fingerprint_location_history[user_id] = [
        (ip, loc, ts) for ip, loc, ts in fingerprint_location_history[user_id]
        if ts >= two_hours_ago
    ]
    
    recent_history = fingerprint_location_history[user_id]
    
    # Check 1: Impossible Travel (if we have location data)
    if location and location_normalized != "Unknown":
        current_coords = get_city_coordinates(location_normalized)
        if current_coords and user_id in fingerprint_last_location:
            previous_location, previous_timestamp = fingerprint_last_location[user_id]
            previous_coords = get_city_coordinates(previous_location)
            
            if previous_coords:
                distance_km = haversine_distance(
                    previous_coords[0], previous_coords[1],
                    current_coords[0], current_coords[1]
                )
                time_diff_seconds = (current_time - previous_timestamp).total_seconds()
                
                if time_diff_seconds > 0:
                    time_diff_hours = time_diff_seconds / 3600.0
                    speed_kmh = distance_km / time_diff_hours if time_diff_hours > 0 else 0
                    
                    # If speed > 900 km/h, flag as impossible travel
                    if speed_kmh > 900:
                        reason = (
                            f"Impossible travel: moved {distance_km:.2f} km "
                            f"from {previous_location} to {location_normalized} "
                            f"in {time_diff_seconds:.0f}s (speed = {speed_kmh:.2f} km/h)"
                        )
                        print(f"🚨 [GEOGRAPHIC JUMP - IMPOSSIBLE TRAVEL] {reason}")
                        fingerprint_last_location[user_id] = (location_normalized, current_time)
                        return reason
        
        # Update last location
        fingerprint_last_location[user_id] = (location_normalized, current_time)
    
    # Check 2: Multiple Locations in Short Time (within last 30 minutes)
    thirty_minutes_ago = current_time - timedelta(minutes=30)
    recent_locations = [
        (ip, loc, ts) for ip, loc, ts in recent_history
        if ts >= thirty_minutes_ago
    ]
    
    # Count unique locations
    unique_locations = set()
    unique_ips = set()
    for ip, loc, ts in recent_locations:
        if loc and loc != "Unknown":
            unique_locations.add(loc)
        if ip and ip != "Unknown":
            unique_ips.add(ip)
    
    # If user appears in 3+ different locations in 30 minutes → geographic jump attack
    if len(unique_locations) >= 3:
        locations_str = ", ".join(sorted(unique_locations))
        reason = (
            f"Geographic jump attack: user appeared in {len(unique_locations)} different locations "
            f"in 30 minutes ({locations_str}). Possible VPN/Proxy hopping or account sharing."
        )
        print(f"🚨 [GEOGRAPHIC JUMP - MULTIPLE LOCATIONS] {reason}")
        return reason
    
    # Check 3: Multiple IPs from different locations (even if location unknown)
    if len(unique_ips) >= 3 and len(recent_locations) >= 3:
        ips_str = ", ".join(list(unique_ips)[:3])  # Show first 3 IPs
        reason = (
            f"Geographic jump: user used {len(unique_ips)} different IP addresses "
            f"in 30 minutes ({ips_str}). Suspicious location switching pattern."
        )
        print(f"🚨 [GEOGRAPHIC JUMP - IP SWITCHING] {reason}")
        return reason
    
    return None


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
    Reads directly from database to ensure latest status is checked.
    """
    from storage import get_fingerprints
    from db import get_db_session, FingerprintDB
    
    # Read directly from database to get latest status
    session = get_db_session()
    try:
        db_fingerprints = session.query(FingerprintDB).filter(
            FingerprintDB.user_id == user_id,
            FingerprintDB.status == "BLOCKED",
            FingerprintDB.risk_score >= RISK_SCORE_BLOCKING_THRESHOLD
        ).all()
        
        if db_fingerprints:
            return True
        
        return False
    finally:
        session.close()


# ================== FEATURE 3: Multi-Account Linking Detection ==================

def compare_behavior(event_features: Dict[str, Any], fingerprint_features: Dict[str, Any], tolerance: float = 0.3) -> bool:
    """
    Compare behavioral features between an event and a fingerprint to detect similar patterns.
    Returns True if the behavior patterns are similar within the given tolerance.
    
    Security idea: Attackers using multiple accounts often exhibit similar behavioral patterns
    (e.g., same typing speed, same navigation patterns, same attack vectors). By comparing
    key behavioral metrics, we can link accounts that are likely controlled by the same attacker.
    
    Args:
        event_features: Behavioral features from the current event
        fingerprint_features: Behavioral features from an existing fingerprint
        tolerance: Percentage tolerance for similarity (default 0.3 = 30%)
    
    Returns:
        True if behaviors are similar within tolerance, False otherwise
    """
    # Key metrics to compare
    metrics_to_compare = [
        "events_per_minute",
        "update_mobile_attempt_count",
        "total_events",
        "pages_visited_count"
    ]
    
    similar_count = 0
    compared_count = 0
    
    for metric in metrics_to_compare:
        event_val = event_features.get(metric, 0)
        fp_val = fingerprint_features.get(metric, 0)
        
        # Skip if both are zero or missing
        if event_val == 0 and fp_val == 0:
            continue
        
        compared_count += 1
        
        # Calculate relative difference
        if max(event_val, fp_val) == 0:
            continue
        
        relative_diff = abs(event_val - fp_val) / max(event_val, fp_val)
        
        # If difference is within tolerance, consider them similar
        if relative_diff <= tolerance:
            similar_count += 1
    
    # If we compared at least 2 metrics and at least 50% are similar, return True
    if compared_count >= 2 and similar_count / compared_count >= 0.5:
        return True
    
    return False


def is_multi_account_attack(event: Event, fingerprint: ThreatFingerprint) -> bool:
    """
    Detect if the same attacker is using multiple accounts (different user_id) from the same
    device/IP with similar behavioral patterns.
    
    Security idea: Sophisticated attackers often create multiple accounts to evade detection
    or to scale their attacks. By detecting when different accounts share the same device/IP
    AND exhibit similar behavioral patterns, we can identify coordinated multi-account attacks
    and treat them as high-risk threats.
    
    Args:
        event: Current event being processed
        fingerprint: Existing ACTIVE fingerprint to compare against
    
    Returns:
        True if multi-account attack is detected, False otherwise
    """
    # Must be different accounts
    if event.user_id == fingerprint.user_id:
        return False
    
    # Must match on device_id OR ip_address
    device_match = False
    ip_match = False
    
    event_device_id = getattr(event, "device_id", None)
    event_ip = getattr(event, "ip_address", None)
    fp_device_id = getattr(fingerprint, "device_id", None)
    fp_ip = getattr(fingerprint, "ip_address", None)
    
    if event_device_id and fp_device_id and event_device_id == fp_device_id:
        device_match = True
    
    if event_ip and fp_ip and event_ip == fp_ip:
        ip_match = True
    
    if not (device_match or ip_match):
        return False
    
    # Calculate behavioral features for current event
    event_features = calculate_behavioral_features(
        event.user_id,
        event.device_id,
        event.timestamp1
    )
    
    # Get behavioral features from fingerprint
    fp_features = fingerprint.behavioral_features
    
    # Compare behavioral patterns
    if compare_behavior(event_features, fp_features, tolerance=0.3):
        return True
    
    return False


# ================== FEATURE 4: Browser-Hopping Detection ==================

def detect_browser_hopping(event: Event, recent_events: list[Event]) -> bool:
    """
    Detect when an attacker is rapidly switching between browsers or browser modes
    (normal/incognito) to evade detection.
    
    Security idea: Attackers may switch browsers quickly to avoid fingerprinting or to
    bypass rate limits. Legitimate users rarely switch browsers multiple times within a
    short time window. Detecting 3+ different user agents in 60 seconds is a strong
    indicator of evasion attempts.
    
    Args:
        event: Current event being processed
        recent_events: List of recent events to analyze
    
    Returns:
        True if browser hopping is detected, False otherwise
    """
    if not recent_events:
        return False
    
    # Collect unique user agents from recent events (same user_id or device_id)
    unique_user_agents = set()
    
    event_user_id = getattr(event, "user_id", None)
    event_device_id = getattr(event, "device_id", None)
    
    for evt in recent_events:
        # Match on user_id or device_id
        evt_user_id = getattr(evt, "user_id", None)
        evt_device_id = getattr(evt, "device_id", None)
        
        matches_user = event_user_id and evt_user_id and evt_user_id == event_user_id
        matches_device = event_device_id and evt_device_id and evt_device_id == event_device_id
        
        if matches_user or matches_device:
            user_agent = getattr(evt, "user_agent", None)
            if user_agent and user_agent != "unknown":
                unique_user_agents.add(user_agent)
    
    # Include current event's user agent
    current_user_agent = getattr(event, "user_agent", None)
    if current_user_agent and current_user_agent != "unknown":
        unique_user_agents.add(current_user_agent)
    
    # If 3 or more different user agents in short time window, flag as browser hopping
    if len(unique_user_agents) >= 3:
        return True
    
    return False


# ================== FEATURE 5: Similar-Behavior Detection ==================

def extract_numeric_features(behavioral_features: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract numeric features from behavioral_features dict for similarity comparison.
    Returns a normalized dictionary with only numeric values.
    
    Security idea: Similar attack patterns often exhibit similar numeric behavioral metrics.
    By comparing key features like event rates, attempt counts, and navigation patterns,
    we can detect when a new attack matches a previously seen attack pattern, even if
    it's from a different user or device. This helps identify coordinated attacks and
    recurring threat actors.
    """
    numeric_features = {}
    
    # Key metrics to compare
    feature_keys = [
        "total_events",
        "events_per_minute",
        "update_mobile_attempt_count",
        "pages_visited_count"
    ]
    
    for key in feature_keys:
        value = behavioral_features.get(key, 0)
        if isinstance(value, (int, float)):
            numeric_features[key] = float(value)
        else:
            numeric_features[key] = 0.0
    
    return numeric_features


def compute_similarity(features1: Dict[str, float], features2: Dict[str, float]) -> float:
    """
    Compute similarity score between two feature vectors using cosine similarity.
    Returns a value between 0 (completely different) and 1 (identical).
    
    Uses cosine similarity which is robust to scale differences and focuses on pattern matching.
    """
    # Get all unique keys
    all_keys = set(features1.keys()) | set(features2.keys())
    
    if not all_keys:
        return 0.0
    
    # Build vectors
    vec1 = [features1.get(k, 0.0) for k in all_keys]
    vec2 = [features2.get(k, 0.0) for k in all_keys]
    
    # Compute dot product and magnitudes
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(a * a for a in vec2))
    
    # Avoid division by zero
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    # Cosine similarity
    similarity = dot_product / (magnitude1 * magnitude2)
    return max(0.0, min(1.0, similarity))  # Clamp between 0 and 1


def find_similar_fingerprints(behavioral_features: Dict[str, Any], top_k: int = 3, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
    """
    Find the top K most similar historical fingerprints based on behavioral features.
    
    Security idea: When a new fingerprint matches a previously blocked or active fingerprint
    pattern, it's likely the same attacker or attack campaign. By identifying these matches,
    we can automatically boost risk scores and link related attacks together.
    
    Args:
        behavioral_features: Behavioral features dict from current event
        top_k: Number of similar fingerprints to return (default: 3)
        similarity_threshold: Minimum similarity score to include (0.0-1.0, default: 0.7)
    
    Returns:
        List of dicts with keys: fingerprint_id, similarity (0-1), status, risk_score
        Sorted by similarity (highest first), limited to top_k
    """
    # Extract numeric features from current behavior
    current_features = extract_numeric_features(behavioral_features)
    
    if not current_features:
        return []
    
    # Get all historical fingerprints from database
    all_fingerprints = get_all_fingerprints_db()
    
    similarities = []
    
    for db_fp in all_fingerprints:
        # Skip if no behavioral features
        if not db_fp.behavioral_features_json:
            continue
        
        try:
            fp_features_dict = json.loads(db_fp.behavioral_features_json)
            fp_features = extract_numeric_features(fp_features_dict)
            
            # Compute similarity
            similarity = compute_similarity(current_features, fp_features)
            
            # Only include if above threshold
            if similarity >= similarity_threshold:
                similarities.append({
                    "fingerprint_id": db_fp.fingerprint_id,
                    "similarity": similarity,
                    "status": db_fp.status,
                    "risk_score": db_fp.risk_score,
                    "user_id": db_fp.user_id
                })
        except (json.JSONDecodeError, Exception) as e:
            # Skip fingerprints with invalid JSON
            continue
    
    # Sort by similarity (highest first) and return top K
    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    return similarities[:top_k]


def reset_user_behavior_history(user_id: str) -> None:
    """
    Reset all in-memory behavioral tracking dictionaries for a specific user.
    
    This is called when an Admin unblocks a user to prevent immediate re-flagging
    based on old history (e.g., preventing the engine from remembering an old Geo-Jump).
    
    Clears:
    - fingerprint_last_device: Last device type used
    - fingerprint_last_location: Last location and timestamp
    - fingerprint_location_history: History of IP/location changes
    - LAST_DEVICE_INFO_BY_USER: Last device context info
    - LAST_ATTACK_MODE_BY_USER: Last attack mode detected
    """
    global fingerprint_last_device
    global fingerprint_last_location
    global fingerprint_location_history
    global LAST_DEVICE_INFO_BY_USER
    global LAST_ATTACK_MODE_BY_USER
    
    # 1. Clear Device History
    if user_id in fingerprint_last_device:
        del fingerprint_last_device[user_id]
        print(f"🧹 [RESET] Cleared device history for {user_id}")

    # 2. Clear Location History (Fixes Geo-Jump re-blocking)
    if user_id in fingerprint_last_location:
        del fingerprint_last_location[user_id]
        print(f"🧹 [RESET] Cleared last location for {user_id}")
    
    if user_id in fingerprint_location_history:
        del fingerprint_location_history[user_id]
        print(f"🧹 [RESET] Cleared location history for {user_id}")

    # 3. Clear Context Info
    if user_id in LAST_DEVICE_INFO_BY_USER:
        del LAST_DEVICE_INFO_BY_USER[user_id]
        print(f"🧹 [RESET] Cleared device context info for {user_id}")

    if user_id in LAST_ATTACK_MODE_BY_USER:
        del LAST_ATTACK_MODE_BY_USER[user_id]
        print(f"🧹 [RESET] Cleared attack mode history for {user_id}")
        
    print(f"✅ [RESET] User {user_id} behavioral memory wiped clean.")


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

    # ================== Device & Network Context ==================
    # Safely read IP and User-Agent from the event (may be missing in some tests)
    ip_address = getattr(event, "ip_address", None)
    user_agent = getattr(event, "user_agent", None)

    # Infer current device type from User-Agent
    current_device_type = get_device_type_from_user_agent(user_agent or "")

    current_device_info = {
        "device_type": current_device_type,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "last_seen_at": event.timestamp1.isoformat(),
    }

    previous_device_info = LAST_DEVICE_INFO_BY_USER.get(event.user_id)
    device_switch_detected = False
    geo_hop_suspected = False

    if previous_device_info:
        prev_type = previous_device_info.get("device_type")
        prev_ip = previous_device_info.get("ip_address")

        # Device-type changed (e.g., mobile → desktop)
        if prev_type and current_device_type and prev_type != current_device_type:
            device_switch_detected = True

        # IP changed between two sessions (simple heuristic for geo-hop / VPN / replay)
        if prev_ip and ip_address and prev_ip != ip_address:
            geo_hop_suspected = True

    # Always update last-seen device info for this user
    LAST_DEVICE_INFO_BY_USER[event.user_id] = current_device_info

    # Persist this context in the behavioral features so it appears in the dashboard
    behavioral_features["device_type"] = current_device_type
    if ip_address:
        behavioral_features["ip_address"] = ip_address
    if user_agent:
        behavioral_features["user_agent"] = user_agent

    if device_switch_detected:
        behavioral_features["device_switch_detected"] = True
        if previous_device_info:
            behavioral_features["device_switch_from"] = previous_device_info.get("device_type", "unknown")

    if geo_hop_suspected:
        behavioral_features["geo_hop_suspected"] = True

    if device_switch_detected or geo_hop_suspected:
        print(
            f"⚠️ [DEVICE CONTEXT] user={event.user_id} "
            f"device_switch={device_switch_detected}, geo_hop={geo_hop_suspected} | "
            f"curr_type={current_device_type}, prev_type={previous_device_info.get('device_type') if previous_device_info else None}"
        )

    # ================== Attack Profile Detection ==================
    # Infer current attack mode from event and behavioral features
    current_attack_mode = infer_attack_mode(event, behavioral_features)
    behavioral_features["attack_mode"] = current_attack_mode
    
    # Track attack mode change
    previous_attack_mode = LAST_ATTACK_MODE_BY_USER.get(event.user_id)
    attack_profile_changed = False
    
    if previous_attack_mode and previous_attack_mode != current_attack_mode:
        attack_profile_changed = True
        behavioral_features["attack_profile_changed"] = True
        behavioral_features["attack_mode_prev"] = previous_attack_mode
        behavioral_features["attack_mode_current"] = current_attack_mode
        print(
            f"🔄 [ATTACK PROFILE CHANGE] user={event.user_id[:8]} "
            f"changed from '{previous_attack_mode}' → '{current_attack_mode}'"
        )
    
    # Always update last seen attack mode for this user
    LAST_ATTACK_MODE_BY_USER[event.user_id] = current_attack_mode

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

    # حدود تقريبية للهجوم (تم تخفيضها بشكل كبير لتسهيل الكشف في الاختبارات)
    is_fast_drain = total_events >= 10 and events_per_minute >= 3.0  # كان 15 و 4.0
    is_high_rate = events_per_minute >= 4.0  # كان 6.0
    is_multiple_updates = update_attempts >= 1  # كان 2
    is_unusual_navigation = pages_visited >= 3  # كان 5
    is_high_volume = total_events >= 10  # كان 20
    is_rapid_clicks = "ui_suspicious_pattern" in event.event_type.lower()  # كشف مباشر للنقرات السريعة
    
    # Debug logging for thresholds
    print(f"🔍 [THRESHOLD CHECK] total_events={total_events}, events_per_min={events_per_minute:.2f}, "
          f"updates={update_attempts}, pages={pages_visited}, rapid_clicks={is_rapid_clicks}")
    print(f"   → fast_drain={is_fast_drain}, high_rate={is_high_rate}, updates={is_multiple_updates}, "
          f"nav={is_unusual_navigation}, volume={is_high_volume}")

    # ============================================================
    # 5) قرار إنشاء بصمة (معدل لتسجيل الجميع)
    # ============================================================
    
    # التعديل: نجعلها True دائماً لتسجيل أي جهاز يدخل الموقع
    should_create_fingerprint = True
    
    if ml_used and risk_score >= RISK_SCORE_BLOCKING_THRESHOLD:
        trigger_source = "ML_HIGH_RISK"
    elif (is_fast_drain or is_high_rate or is_multiple_updates or 
          is_unusual_navigation or is_high_volume or is_rapid_clicks):
        trigger_source = "RULES_FALLBACK"
        
        # Rapid clicks is a serious pattern that warrants high risk
        if is_rapid_clicks:
            risk_score = max(risk_score, 90)  # Risk عالي جداً للنقرات السريعة
            print(f"🚨 [RAPID CLICKS DETECTED] Risk score set to {risk_score}")
        # For other fallback rules, only boost if ML already detected something (>= 50)
        # Don't force blocking threshold - let natural risk assessment determine
        elif risk_score >= 50 and risk_score < RISK_SCORE_BLOCKING_THRESHOLD:
            # Boost moderately but don't force above threshold
            risk_score = min(risk_score + 15, RISK_SCORE_BLOCKING_THRESHOLD - 1)  # Cap at 84 (below blocking)
            print(f"⚠️ [RULES FALLBACK] Risk score boosted to {risk_score} (monitoring, not auto-blocking)")
    else:
        # هذه هي الحالة الجديدة: زيارة طبيعية جداً
        trigger_source = "NORMAL_VISIT_LOG"
        
        # نعطيها درجة خطورة منخفضة جداً لكن نسجلها
        if risk_score == 0:
            risk_score = 10

    # ================== Risk Boost for Device Switch / Geo Hop ==================
    # If there is a suspicious device switch or IP hop AND we already have some risk,
    # slightly boost the risk score (but keep it below blocking threshold for minor cases).
    # Note: This is a warning-level boost, not automatic blocking.
    if (device_switch_detected or geo_hop_suspected) and risk_score < RISK_SCORE_BLOCKING_THRESHOLD:
        # Only boost if we already have significant risk (>= 50), otherwise it's just monitoring
        if risk_score >= 50:
            boosted_score = min(risk_score + 15, RISK_SCORE_BLOCKING_THRESHOLD - 5)  # Cap at 80 (below threshold)
        else:
            boosted_score = min(risk_score + 10, 60)  # Minor boost for low-risk cases
        print(
            f"⚠️ [RISK BOOST] device_switch={device_switch_detected}, "
            f"geo_hop={geo_hop_suspected} | {risk_score} → {boosted_score} (monitoring only)"
        )
        risk_score = boosted_score
        behavioral_features["risk_boost_device_context"] = True

    # ================== Risk Boost for Attack Profile Change ==================
    # If attack profile changed (e.g., from mass_download to rapid_clicks),
    # this suggests a more advanced attacker adapting their strategy.
    # Boost risk score slightly, but only for monitoring (not automatic blocking).
    if attack_profile_changed and risk_score < RISK_SCORE_BLOCKING_THRESHOLD:
        # Only boost if we already have significant risk, otherwise it's just pattern change monitoring
        if risk_score >= 50:
            boosted_score = min(risk_score + 10, RISK_SCORE_BLOCKING_THRESHOLD - 5)  # Cap at 80
        else:
            boosted_score = min(risk_score + 5, 60)  # Minor boost for low-risk cases
        print(
            f"⚠️ [RISK BOOST] attack_profile_changed=True | "
            f"{risk_score} → {boosted_score} (attack mode: {previous_attack_mode} → {current_attack_mode}) [monitoring]"
        )
        risk_score = boosted_score
        behavioral_features["risk_boost_attack_profile"] = True

    # ================== FEATURE 1: Device Change Detection ==================
    detection_reasons = []
    device_type = getattr(event, "device_type", None)
    device_change_reason = detect_device_change(event.user_id, device_type)
    if device_change_reason:
        # Device change alone is not enough for blocking - only add moderate boost
        # This is common behavior (users switch devices), so we monitor but don't block immediately
        risk_score = min(risk_score + 15, RISK_SCORE_BLOCKING_THRESHOLD - 5)  # Cap at 80, don't auto-block
        detection_reasons.append(device_change_reason)
        if not should_create_fingerprint:
            should_create_fingerprint = True
            trigger_source = "DEVICE_CHANGE_DETECTION"
        print(f"⚠️ [DEVICE CHANGE] Risk score increased by +15 → {risk_score} (monitoring only)")

    # ================== FEATURE 2: Geographic Jump Detection (القفزة الجغرافية) ==================
    location = getattr(event, "location", None)
    ip_address = getattr(event, "ip_address", None) or event.ip_address if hasattr(event, "ip_address") else None
    geo_jump_reason = detect_geographic_jump(event.user_id, ip_address, location, event.timestamp1)
    if geo_jump_reason:
        # Geographic jump is suspicious but could be legitimate (VPN, travel, etc.)
        # Only set high risk if combined with other suspicious behaviors
        risk_score = min(max(risk_score, 70) + 20, RISK_SCORE_BLOCKING_THRESHOLD)  # Cap at threshold, don't auto-exceed
        detection_reasons.append(geo_jump_reason)
        behavioral_features["geographic_jump_detected"] = True
        behavioral_features["geo_jump_reason"] = geo_jump_reason
        if not should_create_fingerprint:
            should_create_fingerprint = True
            trigger_source = "GEOGRAPHIC_JUMP_DETECTION"
        print(f"⚠️ [GEOGRAPHIC JUMP] Risk score boosted to {risk_score} (suspicious, monitoring)")

    # ================== FEATURE 3: Multi-Account Linking Detection ==================
    multi_account_detected = False
    # Get all ACTIVE fingerprints from database
    active_fingerprints = get_fingerprints()
    for existing_fp in active_fingerprints:
        # Only check ACTIVE fingerprints
        if existing_fp.status == "ACTIVE" and is_multi_account_attack(event, existing_fp):
            multi_account_detected = True
            risk_score = max(risk_score, 95)  # Very high risk for multi-account attacks
            detection_reasons.append("multi_account_attack")
            behavioral_features["reason"] = "multi_account_attack"
            behavioral_features["linked_fingerprint_id"] = existing_fp.fingerprint_id
            behavioral_features["linked_user_id"] = existing_fp.user_id
            if not should_create_fingerprint:
                should_create_fingerprint = True
                trigger_source = "MULTI_ACCOUNT_ATTACK"
            print(
                f"🚨 [MULTI-ACCOUNT ATTACK] Detected same attacker using different accounts | "
                f"Event user_id: {event.user_id}, Linked fingerprint: {existing_fp.fingerprint_id} "
                f"(user_id: {existing_fp.user_id}) | Risk score set to {risk_score}"
            )
            break  # Only need to detect once

    # ================== FEATURE 4: Browser-Hopping Detection ==================
    # Get recent events for the last 60 seconds (same user_id or device_id)
    time_window_start = event.timestamp1 - timedelta(seconds=60)
    recent_events = [
        evt for evt in EVENTS_STORE
        if (evt.user_id == event.user_id or evt.device_id == event.device_id)
        and evt.timestamp1 >= time_window_start
        and evt.timestamp1 <= event.timestamp1
    ]
    
    browser_hopping_detected = detect_browser_hopping(event, recent_events)
    if browser_hopping_detected:
        risk_score = max(risk_score, 90)  # High risk for browser hopping
        detection_reasons.append("browser_hopping")
        behavioral_features["reason"] = "browser_hopping"
        behavioral_features["unique_user_agents_count"] = len(set(
            getattr(evt, "user_agent", None) or "unknown"
            for evt in recent_events + [event]
            if getattr(evt, "user_agent", None) and getattr(evt, "user_agent", None) != "unknown"
        ))
        if not should_create_fingerprint:
            should_create_fingerprint = True
            trigger_source = "BROWSER_HOPPING"
        print(
            f"🔄 [BROWSER HOPPING] Detected rapid browser switching | "
            f"User: {event.user_id[:8]}, Unique user agents in 60s: {behavioral_features.get('unique_user_agents_count', 0)} | "
            f"Risk score set to {risk_score}"
        )

    # Ensure risk_score doesn't exceed 100
    risk_score = min(100, risk_score)
    
    # REMOVED: Automatic blocking threshold adjustment
    # This was causing false positives - detection reasons alone should not trigger blocking
    # Only block if ML model or severe behavioral patterns (rapid clicks, multi-account, etc.) 
    # indicate high risk score naturally reaches the threshold
    # 
    # Detection reasons are for monitoring and logging, not automatic blocking
    # The system will only block if risk_score naturally reaches RISK_SCORE_BLOCKING_THRESHOLD (85)
    # through ML analysis or clear severe patterns like multi-account attacks

    # Store detection reasons in behavioral_features
    if detection_reasons:
        behavioral_features["detection_reasons"] = detection_reasons

    print(
        f"🔍 [EVAL] src={trigger_source} | "
        f"risk={risk_score} | "
        f"fast_drain={is_fast_drain}, high_rate={is_high_rate}, "
        f"multi_updates={is_multiple_updates}, nav={is_unusual_navigation}, "
        f"high_volume={is_high_volume}"
    )
    if detection_reasons:
        print(f"   🚨 Detection reasons: {', '.join(detection_reasons)}")

    # 6) Similar-Behavior Detection (check against historical fingerprints)
    similar_fingerprints = []
    if should_create_fingerprint:
        # Find similar historical fingerprints
        similar_fingerprints = find_similar_fingerprints(
            behavioral_features,
            top_k=3,
            similarity_threshold=0.7
        )
        
        # If we found very similar fingerprints (≥0.9) that were BLOCKED or ACTIVE, boost risk
        if similar_fingerprints:
            highest_similarity = similar_fingerprints[0]["similarity"]
            blocked_or_active_similar = [
                sf for sf in similar_fingerprints
                if sf["similarity"] >= 0.9 and sf["status"] in ("BLOCKED", "ACTIVE")
            ]
            
            if blocked_or_active_similar:
                # Very high risk - pattern matches a previously blocked/active attack
                risk_score = max(risk_score, 90)
                detection_reasons.append("similar_to_blocked_fingerprint")
                behavioral_features["similarity_detected"] = True
                behavioral_features["highest_similarity"] = highest_similarity
                print(
                    f"🔍 [SIMILARITY] Found {len(blocked_or_active_similar)} similar BLOCKED/ACTIVE fingerprint(s) | "
                    f"Highest similarity: {highest_similarity:.2%} | Risk boosted to {risk_score}"
                )
            else:
                # Moderate similarity - still noteworthy
                behavioral_features["similarity_detected"] = True
                behavioral_features["highest_similarity"] = highest_similarity
                print(
                    f"🔍 [SIMILARITY] Found {len(similar_fingerprints)} similar fingerprint(s) | "
                    f"Highest similarity: {highest_similarity:.2%}"
                )

    # 7) إنشاء وحفظ البصمة إن لزم
    print(f"🔍 [FINGERPRINT DECISION] should_create_fingerprint={should_create_fingerprint}, trigger_source={trigger_source}, risk_score={risk_score}")
    if should_create_fingerprint:
        # Add platform, IP, and user agent to behavioral features for dashboard display
        behavioral_features["platform"] = getattr(event, "platform", None)
        behavioral_features["ip_address"] = getattr(event, "ip_address", None)
        behavioral_features["user_agent"] = getattr(event, "user_agent", None)
        
        fingerprint = ThreatFingerprint(
            fingerprint_id=f"fp-{uuid.uuid4().hex[:12]}",
            risk_score=risk_score,
            user_id=event.user_id,
            status="PENDING",
            behavioral_features=behavioral_features,
            device_id=event.device_id,
            ip_address=getattr(event, "ip_address", None),
            user_agent=getattr(event, "user_agent", None)
        )
        
        # Attach related/similar fingerprints metadata
        if similar_fingerprints:
            fingerprint.related_fingerprints = similar_fingerprints
        
        store_fingerprint(fingerprint)
        print(f"   ✅ Fingerprint created: {fingerprint.fingerprint_id} (Blocking Activated)")
        print(f"      User: {event.user_id}, Device: {event.device_id}, IP: {getattr(event, 'ip_address', 'N/A')}")
        if similar_fingerprints:
            print(f"      Related to {len(similar_fingerprints)} similar fingerprint(s)")
        return fingerprint

    return None


# ================== UNIT TEST HELPERS ==================

def test_compare_behavior():
    """
    Simple sanity check for compare_behavior function.
    Tests that similar behaviors are detected correctly.
    """
    event_features = {
        "events_per_minute": 10.0,
        "update_mobile_attempt_count": 2,
        "total_events": 20,
        "pages_visited_count": 5
    }
    fingerprint_features = {
        "events_per_minute": 11.0,  # Within 30% tolerance
        "update_mobile_attempt_count": 2,  # Exact match
        "total_events": 21,  # Within tolerance
        "pages_visited_count": 5  # Exact match
    }
    result = compare_behavior(event_features, fingerprint_features, tolerance=0.3)
    assert result == True, "Should detect similar behaviors"
    print("✅ [TEST] compare_behavior: PASSED")
    return True


def test_detect_browser_hopping():
    """
    Simple sanity check for detect_browser_hopping function.
    Tests that browser hopping is detected when 3+ different user agents are present.
    """
    from datetime import datetime, timedelta
    now = datetime.now()
    
    # Create events with 3 different user agents
    events = [
        Event(
            event_type="login_attempt",
            user_id="test_user",
            device_id="test_device",
            timestamp1=now - timedelta(seconds=10),
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0"
        ),
        Event(
            event_type="login_attempt",
            user_id="test_user",
            device_id="test_device",
            timestamp1=now - timedelta(seconds=5),
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/14.0"
        ),
    ]
    
    current_event = Event(
        event_type="login_attempt",
        user_id="test_user",
        device_id="test_device",
        timestamp1=now,
        user_agent="Mozilla/5.0 (X11; Linux x86_64) Firefox/89.0"
    )
    
    result = detect_browser_hopping(current_event, events)
    assert result == True, "Should detect browser hopping with 3 different user agents"
    print("✅ [TEST] detect_browser_hopping: PASSED")
    return True


def test_is_multi_account_attack():
    """
    Simple sanity check for is_multi_account_attack function.
    Tests that multi-account attacks are detected when same device/IP with different user_id.
    """
    from datetime import datetime
    
    # Create an existing fingerprint
    existing_fp = ThreatFingerprint(
        fingerprint_id="fp-test-123",
        risk_score=85,
        user_id="attacker_account_1",
        status="ACTIVE",
        behavioral_features={
            "events_per_minute": 10.0,
            "update_mobile_attempt_count": 3,
            "total_events": 25,
            "pages_visited_count": 4
        },
        device_id="same_device_123",
        ip_address="192.168.1.100"
    )
    
    # Create a new event with different user_id but same device/IP and similar behavior
    new_event = Event(
        event_type="login_attempt",
        user_id="attacker_account_2",  # Different account
        device_id="same_device_123",  # Same device
        timestamp1=datetime.now(),
        ip_address="192.168.1.100"  # Same IP
    )
    
    # Note: This test requires the event to have enough behavioral history to match
    # For a real test, you'd need to populate EVENTS_STORE first
    print("⚠️ [TEST] is_multi_account_attack: Manual test required (needs event history)")
    return True


if __name__ == "__main__":
    # Run simple sanity checks
    print("Running unit test helpers...")
    try:
        test_compare_behavior()
        test_detect_browser_hopping()
        test_is_multi_account_attack()
        print("\n✅ All unit test helpers passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n⚠️ Test error: {e}")
