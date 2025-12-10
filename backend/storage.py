# storage.py
"""
In-memory storage layer for events and threat fingerprints.
Used by the engine, API layer, and unit tests.
"""

from typing import List, Optional
from models import Event, ThreatFingerprint

# ========== GLOBAL IN-MEMORY STORES ==========

# All events received by the system (for debugging / feature extraction)
EVENTS_STORE: List[Event] = []

# All threat fingerprints discovered by the engine
FINGERPRINTS_STORE: List[ThreatFingerprint] = []


# ========== EVENT OPERATIONS ==========

def store_event(event: Event) -> None:
    """
    Save a single Event object into the in-memory store.
    """
    EVENTS_STORE.append(event)


# ========== FINGERPRINT OPERATIONS ==========

def store_fingerprint(fingerprint: ThreatFingerprint) -> ThreatFingerprint:
    """
    Save a ThreatFingerprint in memory and return it.
    Tests expect the store size to increase by 1 after this call.
    """
    FINGERPRINTS_STORE.append(fingerprint)
    return fingerprint


def get_fingerprints() -> List[ThreatFingerprint]:
    """
    Return a list of all stored fingerprints.
    Tests use len(FINGERPRINTS_STORE) and len(get_fingerprints()).
    """
    return list(FINGERPRINTS_STORE)


def get_fingerprint_by_id(fingerprint_id: str) -> Optional[ThreatFingerprint]:
    """
    Return a single fingerprint by its ID, or None if not found.
    """
    for fp in FINGERPRINTS_STORE:
        if fp.fingerprint_id == fingerprint_id:
            return fp
    return None


def update_fingerprint_status(fingerprint_id: str, new_status: str) -> bool:
    """
    Update the status of a fingerprint.
    Returns True if updated, False if fingerprint not found.
    """
    fp = get_fingerprint_by_id(fingerprint_id)
    if fp is None:
        return False

    fp.status = new_status
    return True


def clear_user_fingerprints(user_id: str) -> int:
    """
    Set all ACTIVE (or BLOCKED) fingerprints for a given user to CLEARED.
    Returns the number of fingerprints that were updated.
    """
    cleared_count = 0
    print(f"🔓 [UNBLOCK] Clearing fingerprints for user_id: {user_id}")
    for fp in FINGERPRINTS_STORE:
        if fp.user_id == user_id and fp.status in ("ACTIVE", "BLOCKED"):
            print(f"   - Changing fingerprint {fp.fingerprint_id} from {fp.status} to CLEARED")
            fp.status = "CLEARED"
            cleared_count += 1
    print(f"✅ [UNBLOCK] Cleared {cleared_count} fingerprint(s) for user {user_id}")
    return cleared_count


def delete_fingerprint(fingerprint_id: str) -> bool:
    """
    Completely remove a fingerprint from the store.
    Returns True if something was deleted, False otherwise.
    """
    global FINGERPRINTS_STORE

    print(f"🗑️ [DELETE] Attempting to delete fingerprint: {fingerprint_id}")
    for idx, fp in enumerate(FINGERPRINTS_STORE):
        if fp.fingerprint_id == fingerprint_id:
            print(f"   - Found fingerprint {fingerprint_id} for user {fp.user_id}, status: {fp.status}")
            del FINGERPRINTS_STORE[idx]
            print(f"✅ [DELETE] Successfully deleted fingerprint {fingerprint_id}")
            return True

    print(f"⚠️ [DELETE] Fingerprint {fingerprint_id} not found")
    return False
