# storage.py
"""
Storage layer for events and threat fingerprints.
Uses SQLAlchemy database for fingerprints (instead of in-memory).
Events are still kept in-memory for performance (temporary storage for behavioral analysis).
"""

from typing import List, Optional
from datetime import datetime
import json
from models import Event, ThreatFingerprint
from db import FingerprintDB, get_db_session, Session

# ========== GLOBAL IN-MEMORY STORES ==========

# All events received by the system (for debugging / feature extraction)
# Events are kept in-memory temporarily for behavioral feature calculation
EVENTS_STORE: List[Event] = []

# Keep FINGERPRINTS_STORE as a legacy reference for backward compatibility
# But it's now a read-only cache - actual storage is in database
FINGERPRINTS_STORE: List[ThreatFingerprint] = []


# ========== EVENT OPERATIONS ==========

def store_event(event: Event) -> None:
    """
    Save a single Event object into the in-memory store.
    Events are used for behavioral feature calculation and are kept temporarily.
    """
    EVENTS_STORE.append(event)


# ========== FINGERPRINT OPERATIONS (Database-backed) ==========

def store_fingerprint(fingerprint: ThreatFingerprint) -> ThreatFingerprint:
    """
    Save a ThreatFingerprint in the database (insert or update if exists).
    Returns the stored fingerprint.
    """
    session = get_db_session()
    try:
        # Check if fingerprint already exists
        existing = session.query(FingerprintDB).filter(
            FingerprintDB.fingerprint_id == fingerprint.fingerprint_id
        ).first()
        
        if existing:
            # Update existing fingerprint
            existing.user_id = fingerprint.user_id
            existing.device_id = fingerprint.device_id
            existing.ip_address = fingerprint.ip_address
            existing.user_agent = fingerprint.user_agent
            existing.risk_score = fingerprint.risk_score
            existing.status = fingerprint.status
            existing.behavioral_features_json = json.dumps(fingerprint.behavioral_features)
            existing.updated_at = datetime.utcnow()
            
            # Update related_fingerprints if present
            if hasattr(fingerprint, 'related_fingerprints') and fingerprint.related_fingerprints:
                existing.related_fingerprints_json = json.dumps(fingerprint.related_fingerprints)
            
            session.commit()
            print(f"   💾 [DB] Updated fingerprint: {fingerprint.fingerprint_id}")
            return fingerprint
        else:
            # Insert new fingerprint
            related_fingerprints_json = None
            if hasattr(fingerprint, 'related_fingerprints') and fingerprint.related_fingerprints:
                related_fingerprints_json = json.dumps(fingerprint.related_fingerprints)
            
            db_fingerprint = FingerprintDB(
                fingerprint_id=fingerprint.fingerprint_id,
                user_id=fingerprint.user_id,
                device_id=fingerprint.device_id,
                ip_address=fingerprint.ip_address,
                user_agent=fingerprint.user_agent,
                risk_score=fingerprint.risk_score,
                status=fingerprint.status,
                behavioral_features_json=json.dumps(fingerprint.behavioral_features),
                related_fingerprints_json=related_fingerprints_json
            )
            session.add(db_fingerprint)
            session.commit()
            print(f"   💾 [DB] Stored new fingerprint: {fingerprint.fingerprint_id}")
            return fingerprint
    except Exception as e:
        session.rollback()
        print(f"❌ [DB] Error storing fingerprint: {e}")
        raise
    finally:
        session.close()


def get_fingerprints() -> List[ThreatFingerprint]:
    """
    Return a list of all stored fingerprints from the database.
    Converts database models to ThreatFingerprint objects for compatibility.
    """
    session = get_db_session()
    try:
        db_fingerprints = session.query(FingerprintDB).all()
        result = []
        
        for db_fp in db_fingerprints:
            # Convert database model to ThreatFingerprint
            behavioral_features = {}
            if db_fp.behavioral_features_json:
                try:
                    behavioral_features = json.loads(db_fp.behavioral_features_json)
                except json.JSONDecodeError:
                    behavioral_features = {}
            
            fp = ThreatFingerprint(
                fingerprint_id=db_fp.fingerprint_id,
                risk_score=db_fp.risk_score,
                user_id=db_fp.user_id,
                status=db_fp.status,
                behavioral_features=behavioral_features,
                device_id=db_fp.device_id,
                ip_address=db_fp.ip_address,
                user_agent=db_fp.user_agent
            )
            
            # Add related_fingerprints if present
            if db_fp.related_fingerprints_json:
                try:
                    related = json.loads(db_fp.related_fingerprints_json)
                    fp.related_fingerprints = related  # Add as attribute
                except json.JSONDecodeError:
                    pass
            
            result.append(fp)
        
        # Update legacy FINGERPRINTS_STORE for backward compatibility
        global FINGERPRINTS_STORE
        FINGERPRINTS_STORE = result
        
        return result
    finally:
        session.close()


def get_fingerprint_by_id(fingerprint_id: str) -> Optional[ThreatFingerprint]:
    """
    Return a single fingerprint by its ID, or None if not found.
    """
    session = get_db_session()
    try:
        db_fp = session.query(FingerprintDB).filter(
            FingerprintDB.fingerprint_id == fingerprint_id
        ).first()
        
        if not db_fp:
            return None
        
        # Convert to ThreatFingerprint
        behavioral_features = {}
        if db_fp.behavioral_features_json:
            try:
                behavioral_features = json.loads(db_fp.behavioral_features_json)
            except json.JSONDecodeError:
                behavioral_features = {}
        
        fp = ThreatFingerprint(
            fingerprint_id=db_fp.fingerprint_id,
            risk_score=db_fp.risk_score,
            user_id=db_fp.user_id,
            status=db_fp.status,
            behavioral_features=behavioral_features,
            device_id=db_fp.device_id,
            ip_address=db_fp.ip_address,
            user_agent=db_fp.user_agent
        )
        
        # Add related_fingerprints if present
        if db_fp.related_fingerprints_json:
            try:
                related = json.loads(db_fp.related_fingerprints_json)
                fp.related_fingerprints = related
            except json.JSONDecodeError:
                pass
        
        return fp
    finally:
        session.close()


def update_fingerprint_status(fingerprint_id: str, new_status: str) -> bool:
    """
    Update the status of a fingerprint.
    Returns True if updated, False if fingerprint not found.
    """
    session = get_db_session()
    try:
        db_fp = session.query(FingerprintDB).filter(
            FingerprintDB.fingerprint_id == fingerprint_id
        ).first()
        
        if db_fp is None:
            return False
        
        db_fp.status = new_status
        db_fp.updated_at = datetime.utcnow()
        session.commit()
        print(f"   💾 [DB] Updated fingerprint {fingerprint_id} status to {new_status}")
        
        # Update FINGERPRINTS_STORE for backward compatibility
        global FINGERPRINTS_STORE
        for fp in FINGERPRINTS_STORE:
            if fp.fingerprint_id == fingerprint_id:
                fp.status = new_status
                break
        
        return True
    except Exception as e:
        session.rollback()
        print(f"❌ [DB] Error updating fingerprint status: {e}")
        return False
    finally:
        session.close()


def clear_user_fingerprints(user_id: str) -> int:
    """
    Set all ACTIVE (or BLOCKED) fingerprints for a given user to CLEARED.
    Returns the number of fingerprints that were updated.
    """
    session = get_db_session()
    try:
        cleared_count = 0
        print(f"🔓 [UNBLOCK] Clearing fingerprints for user_id: {user_id}")
        
        db_fingerprints = session.query(FingerprintDB).filter(
            FingerprintDB.user_id == user_id,
            FingerprintDB.status.in_(("ACTIVE", "BLOCKED"))
        ).all()
        
        for db_fp in db_fingerprints:
            print(f"   - Changing fingerprint {db_fp.fingerprint_id} from {db_fp.status} to CLEARED")
            db_fp.status = "CLEARED"
            db_fp.updated_at = datetime.utcnow()
            cleared_count += 1
        
        session.commit()
        print(f"✅ [UNBLOCK] Cleared {cleared_count} fingerprint(s) for user {user_id}")
        
        # Update FINGERPRINTS_STORE for backward compatibility
        global FINGERPRINTS_STORE
        for fp in FINGERPRINTS_STORE:
            if fp.user_id == user_id and fp.status in ("ACTIVE", "BLOCKED"):
                fp.status = "CLEARED"
        
        return cleared_count
    except Exception as e:
        session.rollback()
        print(f"❌ [DB] Error clearing user fingerprints: {e}")
        return 0
    finally:
        session.close()


def delete_fingerprint(fingerprint_id: str) -> bool:
    """
    Completely remove a fingerprint from the database.
    Returns True if something was deleted, False otherwise.
    """
    session = get_db_session()
    try:
        print(f"🗑️ [DELETE] Attempting to delete fingerprint: {fingerprint_id}")
        
        db_fp = session.query(FingerprintDB).filter(
            FingerprintDB.fingerprint_id == fingerprint_id
        ).first()
        
        if db_fp:
            print(f"   - Found fingerprint {fingerprint_id} for user {db_fp.user_id}, status: {db_fp.status}")
            session.delete(db_fp)
            session.commit()
            print(f"✅ [DELETE] Successfully deleted fingerprint {fingerprint_id}")
            return True
        else:
            print(f"⚠️ [DELETE] Fingerprint {fingerprint_id} not found")
            return False
    except Exception as e:
        session.rollback()
        print(f"❌ [DB] Error deleting fingerprint: {e}")
        return False
    finally:
        session.close()


def get_all_fingerprints_db() -> List[FingerprintDB]:
    """
    Get all fingerprints as database models (for similarity detection).
    Returns raw FingerprintDB objects from the database.
    """
    session = get_db_session()
    try:
        return session.query(FingerprintDB).all()
    finally:
        session.close()
