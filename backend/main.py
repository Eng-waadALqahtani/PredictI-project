from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os

from models import Event, ThreatFingerprint
from storage import (
    store_event,
    get_fingerprints,
    get_fingerprint_by_id,
    update_fingerprint_status,
    clear_user_fingerprints,
    FINGERPRINTS_STORE,
    delete_fingerprint
)
from engine import process_event, is_user_fingerprinted ,reset_user_behavior_history  
from db import init_db

# ==================  Paths & App Setup  ==================

# Determine the base directory (project root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_PUBLIC = os.path.join(BASE_DIR, 'frontend', 'public')
FRONTEND_JS = os.path.join(BASE_DIR, 'frontend', 'js')

app = Flask(__name__, static_folder=FRONTEND_PUBLIC, static_url_path='')

# Enable CORS for all /api routes with explicit configuration
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})


# Helper function to add CORS headers to responses
def add_cors_headers(response):
    """Add CORS headers to a response"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    return response


# ==================  Static Files Routes  ==================

@app.route('/js/<path:filename>')
def serve_js(filename):
    """Serve JavaScript files"""
    from flask import send_from_directory
    return send_from_directory(FRONTEND_JS, filename)


@app.route('/image/<path:filename>')
def serve_image(filename):
    """Serve image and video files"""
    from flask import send_from_directory
    IMAGE_DIR = os.path.join(BASE_DIR, 'image')

    # Set proper MIME type for video and image files
    if filename.endswith('.mov'):
        response = send_from_directory(IMAGE_DIR, filename, mimetype='video/quicktime')
        response.headers['Accept-Ranges'] = 'bytes'
        return response
    elif filename.endswith('.mp4'):
        response = send_from_directory(IMAGE_DIR, filename, mimetype='video/mp4')
        response.headers['Accept-Ranges'] = 'bytes'
        return response
    elif filename.endswith('.webp'):
        return send_from_directory(IMAGE_DIR, filename, mimetype='image/webp')
    else:
        return send_from_directory(IMAGE_DIR, filename)


# ==================  Events Ingestion  ==================

@app.route('/api/v1/event', methods=['POST', 'OPTIONS'])
def receive_event():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({})), 200
    
    """
    POST /api/v1/event endpoint to receive events.
    1. Receive event from request
    2. store_event
    3. process_event → may generate fingerprint
    """
    try:
        data = request.get_json()
        
        if not data:
            print("❌ [EVENT ERROR] No JSON data received")
            return add_cors_headers(jsonify({"status": "error", "message": "No JSON data provided"})), 400

        # Parse timestamp
        timestamp_str = data.get('timestamp1')
        if isinstance(timestamp_str, str):
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            timestamp = datetime.now()

        # Build event_type
        event_type = data.get('event_type', 'unknown')
        service_name = data.get('service_name')

        if service_name and event_type == "view_service":
            event_type = f"view_service_{service_name}"

        # Capture IP correctly on Render (behind Proxy)
        if request.headers.getlist("X-Forwarded-For"):
            # Render puts the real client IP first in the list
            ip_address = request.headers.getlist("X-Forwarded-For")[0]
        else:
            # Fallback for local development
            ip_address = request.remote_addr or request.environ.get('HTTP_X_FORWARDED_FOR', 'unknown')
            
        # Fallback if specific header is missing/empty
        if not ip_address or ip_address == 'unknown':
            ip_address = request.environ.get('REMOTE_ADDR', 'unknown')
        
        user_agent = request.headers.get("User-Agent", "unknown")
        platform = data.get("platform")
        device_type = data.get("device_type")
        location = data.get("location")

        event = Event(
            event_type=event_type,
            user_id=data.get('user_id', 'unknown'),
            device_id=data.get('device_id', 'unknown'),
            timestamp1=timestamp,
            platform=platform,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_type,
            location=location
        )

        # Store the event
        store_event(event)
        print(f"📥 [EVENT] {event.event_type} from {event.user_id} ({platform})")

        # ==================== BLOCKING ONLY ON PROTECTED PLATFORMS ====================
        # Blocking is only applied on Tawakkalna and Absher platforms
        # Other pages (index, hub, health-portal, etc.) log events but don't block users
        protected_platforms = ["tawakkalna", "absher"]
        is_protected_platform = platform and platform.lower() in protected_platforms
        
        if is_protected_platform:
            # Check if user is already blocked (only on protected platforms)
            is_fingerprinted = is_user_fingerprinted(event.user_id)
            if is_fingerprinted:
                print(f"🚫 [BLOCKED] User {event.user_id} is already blocked on {platform}")
                blocked_response = jsonify({
                    "status": "blocked",
                    "allowed": False,
                    "message": "تم حجب دخولك مؤقتاً بسبب سلوك مشبوه تم رصده على منصة حكومية أخرى"
                })
                return add_cors_headers(blocked_response), 403
        else:
            # On non-protected platforms, log events but skip blocking checks
            print(f"📝 [LOG ONLY] Event logged from {platform} (blocking disabled for this platform)")
            response = {
                "status": "ok",
                "message": "Event processed successfully (logging only)",
                "blocking_disabled": True
            }
            # Still process event for fingerprinting/logging purposes, but don't block
            fingerprint = process_event(event)
            if fingerprint:
                response["fingerprint_generated"] = True
                response["fingerprint_id"] = fingerprint.fingerprint_id
                response["risk_score"] = fingerprint.risk_score
                print(f"✅ [FINGERPRINT] ID: {fingerprint.fingerprint_id}, Risk: {fingerprint.risk_score} (monitoring only)")
            return add_cors_headers(jsonify(response)), 200
        # ==============================================================================

        # Process the event through the threat engine
        fingerprint = process_event(event)

        # ==================== LOGIC UPDATE FOR LOGGING ALL VISITS ====================
        # Calculate behavioral features for checking (only on protected platforms)
        from engine import calculate_behavioral_features, RISK_SCORE_BLOCKING_THRESHOLD
        
        behavioral_features = calculate_behavioral_features(
            event.user_id,
            event.device_id,
            event.timestamp1
        )
        
        total_events = behavioral_features.get("total_events", 0)
        events_per_minute = behavioral_features.get("events_per_minute", 0.0)
        update_attempts = behavioral_features.get("update_mobile_attempt_count", 0)
        
        # Immediate blocking conditions (only on protected platforms)
        should_block_immediately = False
        block_reason = None
        
        # Priority 1: Trust the Fingerprint Risk Score (Source of Truth)
        if fingerprint:
            if fingerprint.risk_score >= RISK_SCORE_BLOCKING_THRESHOLD:
                should_block_immediately = True
                block_reason = f"High risk fingerprint created (risk_score: {fingerprint.risk_score})"
            # Important: If fingerprint exists but risk is low, DO NOT BLOCK.
            # This allows safe users to be logged without being blocked.
            
        # Priority 2: Fallback Rules (Only if NO fingerprint was generated)
        # We increased thresholds here to avoid accidental blocking of normal users
        elif total_events >= 50 or events_per_minute >= 20 or update_attempts >= 5:
            should_block_immediately = True
            block_reason = f"Suspicious behavior fallback (events: {total_events}, rate: {events_per_minute:.1f}/min)"
        
        if should_block_immediately:
            print(f"🚫 [IMMEDIATE BLOCK] User {event.user_id} blocked on {platform} due to: {block_reason}")
            blocked_response = jsonify({
                "status": "blocked",
                "allowed": False,
                "message": "تم حجب دخولك مؤقتاً بسبب سلوك مشبوه تم رصده على منصة حكومية أخرى",
                "reason": block_reason
            })
            return add_cors_headers(blocked_response), 403
        # ==============================================================================

        response = {
            "status": "ok",
            "message": "Event processed successfully"
        }

        if fingerprint:
            response["fingerprint_generated"] = True
            response["fingerprint_id"] = fingerprint.fingerprint_id
            response["risk_score"] = fingerprint.risk_score
            print(f"✅ [FINGERPRINT] ID: {fingerprint.fingerprint_id}, Risk: {fingerprint.risk_score}")
        else:
            response["fingerprint_generated"] = False

        return add_cors_headers(jsonify(response)), 200

    except Exception as e:
        print(f"❌ [ERROR] receive_event: {e}")
        error_response = jsonify({
            "status": "error",
            "message": str(e)
        })
        return add_cors_headers(error_response), 400


# ==================  Fingerprints API  ==================

@app.route('/api/v1/fingerprints', methods=['GET', 'OPTIONS'])
def get_all_fingerprints():
    """GET /api/v1/fingerprints - Returns all fingerprints for dashboard."""
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({})), 200

    try:
        try:
            fingerprints = get_fingerprints()
        except Exception as inner_e:
            print(f"⚠️ [WARN] get_fingerprints() failed: {inner_e}")
            fingerprints = None

        if fingerprints is None:
            fingerprints = FINGERPRINTS_STORE

        if not isinstance(fingerprints, (list, tuple)):
            fingerprints = []

        fingerprints_data = []
        for fp in fingerprints:
            try:
                if isinstance(fp, ThreatFingerprint):
                    fingerprints_data.append(fp.to_dict())
                elif isinstance(fp, dict):
                    fingerprints_data.append(fp)
            except Exception:
                continue

        return add_cors_headers(jsonify(fingerprints_data)), 200

    except Exception as e:
        print(f"❌ [ERROR] Error getting fingerprints: {e}")
        return add_cors_headers(jsonify({"status": "error", "message": str(e), "fingerprints": []})), 500


@app.route('/api/v1/debug', methods=['GET'])
def debug_status():
    """Simple debug endpoint."""
    from storage import EVENTS_STORE, FINGERPRINTS_STORE
    try:
        return jsonify({
            "status": "ok",
            "events_count": len(EVENTS_STORE),
            "fingerprints_count": len(FINGERPRINTS_STORE)
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/v1/check-user-status', methods=['POST', 'OPTIONS'])
def check_user_status():
    """Check detailed status of a user"""
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({})), 200
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        if not user_id:
            return add_cors_headers(jsonify({"status": "error", "message": "user_id required"})), 400

        from storage import FINGERPRINTS_STORE
        user_fingerprints = [fp for fp in FINGERPRINTS_STORE if fp.user_id == user_id]
        from engine import RISK_SCORE_BLOCKING_THRESHOLD
        active_blocking = [fp for fp in user_fingerprints 
                          if fp.status == "ACTIVE" and fp.risk_score >= RISK_SCORE_BLOCKING_THRESHOLD]
        
        return add_cors_headers(jsonify({
            "status": "ok",
            "user_id": user_id,
            "is_blocked": len(active_blocking) > 0,
            "total_fingerprints": len(user_fingerprints)
        })), 200
    except Exception as e:
        return add_cors_headers(jsonify({"status": "error", "message": str(e)})), 500


# ==================  HTML Pages Routes  ==================

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/health-portal.html')
def health_portal():
    return app.send_static_file('health-portal.html')

@app.route('/dashboard.html')
def dashboard():
    return app.send_static_file('dashboard.html')

@app.route('/absher-login')
def absher_login():
    return app.send_static_file('absher-login.html')

@app.route('/tawakkalna-login.html')
def tawakkalna_login_page():
    return app.send_static_file('tawakkalna-login.html')

@app.route('/tawakkalna-services.html')
def tawakkalna_services_page():
    return app.send_static_file('tawakkalna-services.html')

@app.route('/absher-login.html')
def absher_login_page():
    return app.send_static_file('absher-login.html')

@app.route('/soc-admin-dashboard.html')
def soc_admin_dashboard():
    return app.send_static_file('soc-admin-dashboard.html')

@app.route('/hub.html')
def hub():
    return app.send_static_file('hub.html')

@app.route('/database-view.html')
def database_view():
    return app.send_static_file('database-view.html')

@app.route('/vpn-test.html')
def vpn_test():
    return app.send_static_file('vpn-test.html')


@app.route('/api/v1/database-stats', methods=['GET'])
def get_database_stats():
    """Get database statistics."""
    from db import get_db_session, FingerprintDB
    from sqlalchemy import func
    try:
        session = get_db_session()
        total = session.query(FingerprintDB).count()
        active = session.query(FingerprintDB).filter(FingerprintDB.status == "ACTIVE").count()
        blocked = session.query(FingerprintDB).filter(FingerprintDB.status == "BLOCKED").count()
        
        from engine import RISK_SCORE_BLOCKING_THRESHOLD
        high_risk = session.query(FingerprintDB).filter(FingerprintDB.risk_score >= RISK_SCORE_BLOCKING_THRESHOLD).count()
        
        session.close()
        return add_cors_headers(jsonify({
            "status": "ok",
            "statistics": {
                "total_fingerprints": total,
                "by_status": {"active": active, "blocked": blocked},
                "by_risk_level": {"high": high_risk}
            }
        })), 200
    except Exception as e:
        return add_cors_headers(jsonify({"status": "error", "message": str(e)})), 500


# ==================  Blocking / Unblocking APIs  ==================

@app.route('/api/v1/check-and-login', methods=['POST', 'OPTIONS'])
def check_and_login():
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({})), 200
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        if not user_id:
            return add_cors_headers(jsonify({"status": "error", "message": "user_id required"})), 400

        is_fingerprinted = is_user_fingerprinted(user_id)
        
        if is_fingerprinted:
            blocked_response = jsonify({
                "status": "blocked",
                "allowed": False,
                "message": "تم حجب دخولك مؤقتاً بسبب سلوك مشبوه"
            })
            return add_cors_headers(blocked_response), 403
        else:
            return add_cors_headers(jsonify({"status": "ok", "allowed": True, "message": "تم التحقق بنجاح"})), 200
    except Exception as e:
        return add_cors_headers(jsonify({"status": "error", "message": str(e)})), 500


@app.route('/api/v1/unblock-user', methods=['POST', 'OPTIONS'])
def unblock_user():
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({})), 200
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        if not user_id:
            return add_cors_headers(jsonify({"status": "error", "message": "user_id required"})), 400

        cleared_count = clear_user_fingerprints(user_id)
        reset_user_behavior_history(user_id)

        return add_cors_headers(jsonify({
            "status": "ok", 
            "message": f"تم إزالة المنع وتصفير السجل السلوكي للمستخدم {user_id}",
            "cleared_fingerprints": cleared_count
        })), 200
    except Exception as e:
        return add_cors_headers(jsonify({"status": "error", "message": str(e)})), 500


@app.route('/api/v1/confirm-threat', methods=['POST', 'OPTIONS'])
def confirm_threat():
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({})), 200
    try:
        data = request.get_json()
        fingerprint_id = data.get('fingerprint_id')
        if not fingerprint_id:
            return add_cors_headers(jsonify({"status": "error", "message": "fingerprint_id required"})), 400

        success = update_fingerprint_status(fingerprint_id, "BLOCKED")
        if not success:
            return add_cors_headers(jsonify({"status": "error", "message": "Fingerprint not found"})), 404

        return add_cors_headers(jsonify({
            "status": "ok", 
            "message": f"تم تأكيد التهديد للبصمة {fingerprint_id}",
            "new_status": "BLOCKED"
        })), 200
    except Exception as e:
        return add_cors_headers(jsonify({"status": "error", "message": str(e)})), 500


@app.route('/api/v1/clear-fingerprint', methods=['POST', 'OPTIONS'])
def clear_fingerprint_route():
    """Clear a fingerprint (set status to CLEARED)"""
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({})), 200
    try:
        data = request.get_json()
        fingerprint_id = data.get('fingerprint_id')
        if not fingerprint_id:
            return add_cors_headers(jsonify({"status": "error", "message": "fingerprint_id required"})), 400

        success = update_fingerprint_status(fingerprint_id, "CLEARED")
        if not success:
            return add_cors_headers(jsonify({"status": "error", "message": "Fingerprint not found"})), 404

        return add_cors_headers(jsonify({"status": "ok", "message": "تم إزالة التنبيه للبصمة"})), 200
    except Exception as e:
        return add_cors_headers(jsonify({"status": "error", "message": str(e)})), 500


@app.route('/api/v1/delete-fingerprint', methods=['POST', 'OPTIONS'])
def delete_fingerprint_route():
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({})), 200
    try:
        data = request.get_json()
        fingerprint_id = data.get('fingerprint_id')
        if not fingerprint_id:
            return add_cors_headers(jsonify({"status": "error", "message": "fingerprint_id required"})), 400

        success = delete_fingerprint(fingerprint_id)
        if not success:
            return add_cors_headers(jsonify({"status": "error", "message": "Fingerprint not found"})), 404

        return add_cors_headers(jsonify({"status": "ok", "message": "تم حذف البصمة"})), 200
    except Exception as e:
        return add_cors_headers(jsonify({"status": "error", "message": str(e)})), 500


@app.route('/api/v1/health', methods=['GET', 'OPTIONS'])
def health_check():
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({})), 200
    return add_cors_headers(jsonify({"ok": True})), 200


# ==================  App Entry  ==================

if __name__ == '__main__':
    init_db()
    model_dir = os.path.join(os.path.dirname(__file__), '..', 'ml', 'models')
    os.makedirs(model_dir, exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)