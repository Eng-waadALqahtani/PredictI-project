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
    for fp in FINGERPRINTS_STORE:
        if fp.user_id == user_id and fp.status in ("ACTIVE", "BLOCKED"):
            fp.status = "CLEARED"
            cleared_count += 1
    return cleared_count


def delete_fingerprint(fingerprint_id: str) -> bool:
    """
    Completely remove a fingerprint from the store.
    Returns True if something was deleted, False otherwise.
    """
    global FINGERPRINTS_STORE

    for idx, fp in enumerate(FINGERPRINTS_STORE):
        if fp.fingerprint_id == fingerprint_id:
            del FINGERPRINTS_STORE[idx]
            return True

    return False
