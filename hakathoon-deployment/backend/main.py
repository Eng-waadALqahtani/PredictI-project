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
from engine import process_event, is_user_fingerprinted

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

        # Parse timestamp from ISO format string
        timestamp_str = data.get('timestamp1')
        if isinstance(timestamp_str, str):
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            timestamp = datetime.now()

        # Build event_type (optionally attach service_name)
        event_type = data.get('event_type', 'unknown')
        service_name = data.get('service_name')

        if service_name and event_type == "view_service":
            event_type = f"view_service_{service_name}"

        # Capture IP address and User-Agent from request
        ip_address = request.remote_addr or request.environ.get('HTTP_X_FORWARDED_FOR', 'unknown')
        if ip_address == 'unknown' or not ip_address:
            ip_address = request.environ.get('REMOTE_ADDR', 'unknown')
        
        user_agent = request.headers.get("User-Agent", "unknown")
        platform = data.get("platform")

        event = Event(
            event_type=event_type,
            user_id=data.get('user_id', 'unknown'),
            device_id=data.get('device_id', 'unknown'),
            timestamp1=timestamp,
            platform=platform,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Store the event
        store_event(event)
        print(
            f"📥 [EVENT RECEIVED] Type: {event.event_type}, "
            f"User: {event.user_id[:12]}..., Device: {event.device_id[:12]}..."
        )

        # Process the event through the threat engine
        fingerprint = process_event(event)

        response = {
            "status": "ok",
            "message": "Event processed successfully"
        }

        if fingerprint:
            response["fingerprint_generated"] = True
            response["fingerprint_id"] = fingerprint.fingerprint_id
            print(
                f"✅ [FINGERPRINT CREATED] ID: {fingerprint.fingerprint_id}, "
                f"Risk: {fingerprint.risk_score}"
            )
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
    """
    GET /api/v1/fingerprints
    Returns all ThreatFingerprint objects in JSON format for the dashboard.
    """
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({})), 200

    try:
        # Try using get_fingerprints(); if it fails, fall back to FINGERPRINTS_STORE
        try:
            fingerprints = get_fingerprints()
        except Exception as inner_e:
            print(f"⚠️ [WARN] get_fingerprints() failed, using FINGERPRINTS_STORE instead: {inner_e}")
            fingerprints = None

        if fingerprints is None:
            fingerprints = FINGERPRINTS_STORE

        if not isinstance(fingerprints, (list, tuple)):
            print(f"⚠️ [WARN] Unexpected fingerprints type: {type(fingerprints)} → using empty list")
            fingerprints = []

        fingerprints_data = []
        for fp in fingerprints:
            try:
                if isinstance(fp, ThreatFingerprint):
                    fingerprints_data.append(fp.to_dict())
                elif isinstance(fp, dict):
                    fingerprints_data.append(fp)
                else:
                    print(f"⚠️ [WARN] Unknown fingerprint object type: {type(fp)} → skipping")
            except Exception as conv_e:
                print(f"❌ [ERROR] Failed to convert fingerprint to dict: {conv_e}")
                continue

        print(f"📊 [DEBUG] Returning {len(fingerprints_data)} fingerprints to dashboard")

        return add_cors_headers(jsonify(fingerprints_data)), 200

    except Exception as e:
        print(f"❌ [ERROR] Error getting fingerprints: {e}")
        import traceback
        traceback.print_exc()
        error_response = jsonify({
            "status": "error",
            "message": str(e),
            "fingerprints": []
        })
        return add_cors_headers(error_response), 500


@app.route('/api/v1/debug', methods=['GET'])
def debug_status():
    """Simple debug endpoint."""
    from storage import EVENTS_STORE, FINGERPRINTS_STORE

    try:
        return jsonify({
            "status": "ok",
            "events_count": len(EVENTS_STORE),
            "fingerprints_count": len(FINGERPRINTS_STORE),
            "recent_events": [
                {
                    "event_type": e.event_type,
                    "user_id": e.user_id,
                    "timestamp": e.timestamp1.isoformat()
                }
                for e in EVENTS_STORE[-10:]
            ],
            "fingerprints": [
                fp.to_dict() if isinstance(fp, ThreatFingerprint) else str(fp)
                for fp in FINGERPRINTS_STORE
            ]
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ==================  HTML Pages Routes  ==================

@app.route('/')
def index():
    """Serve the main index page with links to all pages"""
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


@app.route('/absher-login.html')
def absher_login_page():
    return app.send_static_file('absher-login.html')


@app.route('/soc-admin-dashboard.html')
def soc_admin_dashboard():
    """Redirect old SOC page to unified dashboard"""
    return app.send_static_file('dashboard.html')


@app.route('/hub.html')
def hub():
    return app.send_static_file('hub.html')


# ==================  Blocking / Unblocking APIs  ==================

@app.route('/api/v1/check-and-login', methods=['POST', 'OPTIONS'])
def check_and_login():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({})), 200
    """
    Check if user is fingerprinted (blocked) before login.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            error_response = jsonify({
                "status": "error",
                "message": "user_id is required"
            })
            return add_cors_headers(error_response), 400

        is_fingerprinted = is_user_fingerprinted(user_id)

        if is_fingerprinted:
            blocked_response = jsonify({
                "status": "blocked",
                "allowed": False,
                "message": "تم حجب دخولك مؤقتاً بسبب سلوك مشبوه تم رصده على منصة حكومية أخرى"
            })
            return add_cors_headers(blocked_response), 403
        else:
            success_response = jsonify({
                "status": "ok",
                "allowed": True,
                "message": "تم التحقق بنجاح"
            })
            return add_cors_headers(success_response), 200

    except Exception as e:
        error_response = jsonify({
            "status": "error",
            "message": str(e)
        })
        return add_cors_headers(error_response), 500


@app.route('/api/v1/unblock-user', methods=['POST', 'OPTIONS'])
def unblock_user():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({})), 200
    """
    Clear all ACTIVE fingerprints for a given user.
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            error_response = jsonify({
                "status": "error",
                "message": "user_id is required"
            })
            return add_cors_headers(error_response), 400

        cleared_count = clear_user_fingerprints(user_id)

        success_response = jsonify({
            "status": "ok",
            "message": f"تم إزالة المنع للمستخدم {user_id}",
            "cleared_fingerprints": cleared_count
        })
        return add_cors_headers(success_response), 200

    except Exception as e:
        error_response = jsonify({
            "status": "error",
            "message": str(e)
        })
        return add_cors_headers(error_response), 500


@app.route('/api/v1/confirm-threat', methods=['POST', 'OPTIONS'])
def confirm_threat():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({})), 200
    """
    Confirm a threat fingerprint (set status to BLOCKED).
    """
    try:
        data = request.get_json()
        fingerprint_id = data.get('fingerprint_id')

        if not fingerprint_id:
            error_response = jsonify({
                "status": "error",
                "message": "fingerprint_id is required"
            })
            return add_cors_headers(error_response), 400

        success = update_fingerprint_status(fingerprint_id, "BLOCKED")

        if not success:
            not_found_response = jsonify({
                "status": "error",
                "message": f"Fingerprint {fingerprint_id} not found"
            })
            return add_cors_headers(not_found_response), 404

        success_response = jsonify({
            "status": "ok",
            "message": f"تم تأكيد التهديد للبصمة {fingerprint_id}",
            "fingerprint_id": fingerprint_id,
            "new_status": "BLOCKED"
        })
        return add_cors_headers(success_response), 200

    except Exception as e:
        error_response = jsonify({
            "status": "error",
            "message": str(e)
        })
        return add_cors_headers(error_response), 500


@app.route('/api/v1/delete-fingerprint', methods=['POST', 'OPTIONS'])
def delete_fingerprint_route():
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return add_cors_headers(jsonify({})), 200
    """
    Delete a single fingerprint from the store.
    """
    try:
        data = request.get_json()
        fingerprint_id = data.get('fingerprint_id')

        if not fingerprint_id:
            error_response = jsonify({
                "status": "error",
                "message": "fingerprint_id is required"
            })
            return add_cors_headers(error_response), 400

        success = delete_fingerprint(fingerprint_id)

        if not success:
            not_found_response = jsonify({
                "status": "error",
                "message": f"Fingerprint {fingerprint_id} not found"
            })
            return add_cors_headers(not_found_response), 404

        success_response = jsonify({
            "status": "ok",
            "message": f"تم حذف البصمة {fingerprint_id} من الذاكرة"
        })
        return add_cors_headers(success_response), 200

    except Exception as e:
        error_response = jsonify({
            "status": "error",
            "message": str(e)
        })
        return add_cors_headers(error_response), 500


# ==================  App Entry  ==================

if __name__ == '__main__':
    # Ensure the ml/models directory exists
    model_dir = os.path.join(os.path.dirname(__file__), '..', 'ml', 'models')
    os.makedirs(model_dir, exist_ok=True)

    # Use PORT environment variable for Render, default to 5000 for local development
    port = int(os.environ.get('PORT', 5000))
    # Disable debug mode in production (Render sets environment variables)
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug)
