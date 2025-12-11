"""
Test script to verify all features of PredictIQ:
1. Database operations
2. Multi-account linking detection
3. Browser-hopping detection
4. Similar-behavior detection
5. Risk scoring and fingerprint creation

Run: python backend/test_features.py
"""

import sys
import os
from datetime import datetime, timedelta
import json

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from models import Event, ThreatFingerprint
from storage import store_event, store_fingerprint, get_fingerprints, clear_user_fingerprints
from engine import process_event, find_similar_fingerprints
from db import init_db, get_db_session, FingerprintDB

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def test_database_initialization():
    """Test 1: Database initialization"""
    print_header("TEST 1: Database Initialization")
    try:
        init_db()
        print_success("Database initialized successfully")
        
        # Check if tables exist
        session = get_db_session()
        try:
            count = session.query(FingerprintDB).count()
            print_info(f"Current fingerprints in database: {count}")
            return True
        finally:
            session.close()
    except Exception as e:
        print_error(f"Database initialization failed: {e}")
        return False

def test_basic_fingerprint_storage():
    """Test 2: Basic fingerprint storage"""
    print_header("TEST 2: Basic Fingerprint Storage")
    try:
        # Create a test fingerprint
        test_fp = ThreatFingerprint(
            fingerprint_id="fp-test-001",
            risk_score=85,
            user_id="test_user_1",
            status="ACTIVE",
            behavioral_features={
                "total_events": 25,
                "events_per_minute": 10.5,
                "update_mobile_attempt_count": 3,
                "pages_visited_count": 5
            },
            device_id="device-001",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0"
        )
        
        stored = store_fingerprint(test_fp)
        print_success(f"Fingerprint stored: {stored.fingerprint_id}")
        
        # Retrieve it
        all_fps = get_fingerprints()
        found = [fp for fp in all_fps if fp.fingerprint_id == "fp-test-001"]
        if found:
            print_success(f"Fingerprint retrieved: {found[0].fingerprint_id}, Risk: {found[0].risk_score}")
            return True
        else:
            print_error("Fingerprint not found after storage")
            return False
    except Exception as e:
        print_error(f"Fingerprint storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multi_account_detection():
    """Test 3: Multi-account linking detection"""
    print_header("TEST 3: Multi-Account Linking Detection")
    try:
        # First, create a fingerprint for user_1
        base_time = datetime.now()
        event1 = Event(
            event_type="login_attempt",
            user_id="attacker_account_1",
            device_id="same_device_123",
            timestamp1=base_time,
            ip_address="192.168.1.50",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0"
        )
        store_event(event1)
        
        # Process first event to create fingerprint
        fp1 = process_event(event1)
        if fp1:
            print_success(f"Created first fingerprint: {fp1.fingerprint_id} for user: {fp1.user_id}")
        else:
            # Manually create one for testing
            fp1 = ThreatFingerprint(
                fingerprint_id="fp-multi-001",
                risk_score=80,
                user_id="attacker_account_1",
                status="ACTIVE",
                behavioral_features={
                    "total_events": 20,
                    "events_per_minute": 8.0,
                    "update_mobile_attempt_count": 2,
                    "pages_visited_count": 4
                },
                device_id="same_device_123",
                ip_address="192.168.1.50"
            )
            store_fingerprint(fp1)
            print_info("Created test fingerprint manually")
        
        # Now create event for different user but same device/IP
        event2 = Event(
            event_type="login_attempt",
            user_id="attacker_account_2",  # Different user
            device_id="same_device_123",    # Same device
            timestamp1=base_time + timedelta(seconds=10),
            ip_address="192.168.1.50",     # Same IP
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0"
        )
        store_event(event2)
        
        # Process second event - should detect multi-account attack
        fp2 = process_event(event2)
        if fp2:
            print_success(f"Created second fingerprint: {fp2.fingerprint_id}")
            if fp2.risk_score >= 95:
                print_success(f"✅ Multi-account attack detected! Risk score: {fp2.risk_score}")
                return True
            else:
                print_warning(f"Multi-account not detected (risk: {fp2.risk_score})")
                return False
        else:
            print_warning("No fingerprint created for second event")
            return False
    except Exception as e:
        print_error(f"Multi-account detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_browser_hopping_detection():
    """Test 4: Browser-hopping detection"""
    print_header("TEST 4: Browser-Hopping Detection")
    try:
        base_time = datetime.now()
        user_id = "browser_hopper_user"
        device_id = "device-browser-001"
        
        # Create events with different user agents in short time window
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/14.0",
            "Mozilla/5.0 (X11; Linux x86_64) Firefox/89.0"
        ]
        
        for i, ua in enumerate(user_agents):
            event = Event(
                event_type="login_attempt",
                user_id=user_id,
                device_id=device_id,
                timestamp1=base_time + timedelta(seconds=i * 5),  # 5 seconds apart
                user_agent=ua
            )
            store_event(event)
        
        # Process the last event - should detect browser hopping
        last_event = Event(
            event_type="view_service",
            user_id=user_id,
            device_id=device_id,
            timestamp1=base_time + timedelta(seconds=20),
            user_agent=user_agents[2]
        )
        
        fp = process_event(last_event)
        if fp:
            print_success(f"Created fingerprint: {fp.fingerprint_id}")
            if fp.risk_score >= 90:
                print_success(f"✅ Browser hopping detected! Risk score: {fp.risk_score}")
                return True
            else:
                print_warning(f"Browser hopping not detected (risk: {fp.risk_score})")
                return False
        else:
            print_warning("No fingerprint created")
            return False
    except Exception as e:
        print_error(f"Browser-hopping detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_similar_behavior_detection():
    """Test 5: Similar-behavior detection"""
    print_header("TEST 5: Similar-Behavior Detection")
    try:
        # Create a blocked fingerprint with specific pattern
        blocked_fp = ThreatFingerprint(
            fingerprint_id="fp-blocked-001",
            risk_score=95,
            user_id="blocked_user",
            status="BLOCKED",
            behavioral_features={
                "total_events": 30,
                "events_per_minute": 12.0,
                "update_mobile_attempt_count": 4,
                "pages_visited_count": 6
            },
            device_id="device-blocked",
            ip_address="10.0.0.1"
        )
        store_fingerprint(blocked_fp)
        print_success(f"Created blocked fingerprint: {blocked_fp.fingerprint_id}")
        
        # Now create a new event with similar behavior
        base_time = datetime.now()
        similar_event = Event(
            event_type="login_attempt",
            user_id="new_attacker",
            device_id="device-new",
            timestamp1=base_time,
            ip_address="10.0.0.2"
        )
        store_event(similar_event)
        
        # Manually test similarity detection
        test_features = {
            "total_events": 28,  # Similar to 30
            "events_per_minute": 11.5,  # Similar to 12.0
            "update_mobile_attempt_count": 4,  # Same
            "pages_visited_count": 5  # Similar to 6
        }
        
        similar = find_similar_fingerprints(test_features, top_k=3, similarity_threshold=0.7)
        print_info(f"Found {len(similar)} similar fingerprints")
        
        if similar:
            for sim in similar:
                print_info(f"  - {sim['fingerprint_id']}: similarity={sim['similarity']:.2%}, status={sim['status']}")
            
            # Check if we found the blocked one
            blocked_similar = [s for s in similar if s['status'] == 'BLOCKED']
            if blocked_similar:
                print_success(f"✅ Found similar BLOCKED fingerprint! Similarity: {blocked_similar[0]['similarity']:.2%}")
                return True
            else:
                print_warning("Found similar fingerprints but none are BLOCKED")
                return False
        else:
            print_warning("No similar fingerprints found")
            return False
    except Exception as e:
        print_error(f"Similar-behavior detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_risk_score_boost():
    """Test 6: Risk score boost from similarity"""
    print_header("TEST 6: Risk Score Boost from Similarity")
    try:
        # Create a blocked fingerprint
        blocked_fp = ThreatFingerprint(
            fingerprint_id="fp-blocked-002",
            risk_score=95,
            user_id="blocked_user_2",
            status="BLOCKED",
            behavioral_features={
                "total_events": 25,
                "events_per_minute": 10.0,
                "update_mobile_attempt_count": 3,
                "pages_visited_count": 5
            }
        )
        store_fingerprint(blocked_fp)
        
        # Create event with similar behavior
        base_time = datetime.now()
        event = Event(
            event_type="login_attempt",
            user_id="new_user_similar",
            device_id="device-similar",
            timestamp1=base_time,
            ip_address="192.168.1.200"
        )
        store_event(event)
        
        # Process event - should detect similarity and boost risk
        fp = process_event(event)
        if fp:
            print_success(f"Created fingerprint: {fp.fingerprint_id}")
            print_info(f"Risk score: {fp.risk_score}")
            
            # Check if related_fingerprints is set
            if hasattr(fp, 'related_fingerprints') and fp.related_fingerprints:
                print_success(f"✅ Similarity detected! Found {len(fp.related_fingerprints)} related fingerprints")
                if fp.risk_score >= 90:
                    print_success(f"✅ Risk score boosted to {fp.risk_score} (due to similarity to BLOCKED fingerprint)")
                    return True
                else:
                    print_warning(f"Risk score not boosted enough: {fp.risk_score}")
                    return False
            else:
                print_warning("No related fingerprints found")
                return False
        else:
            print_warning("No fingerprint created")
            return False
    except Exception as e:
        print_error(f"Risk score boost test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_operations():
    """Test 7: Database operations (update, delete, clear)"""
    print_header("TEST 7: Database Operations")
    try:
        from storage import update_fingerprint_status, delete_fingerprint, get_fingerprint_by_id
        
        # Create a test fingerprint
        test_fp = ThreatFingerprint(
            fingerprint_id="fp-db-test-001",
            risk_score=75,
            user_id="db_test_user",
            status="ACTIVE",
            behavioral_features={"total_events": 10}
        )
        store_fingerprint(test_fp)
        print_success("Created test fingerprint")
        
        # Test update status
        updated = update_fingerprint_status("fp-db-test-001", "BLOCKED")
        if updated:
            fp = get_fingerprint_by_id("fp-db-test-001")
            if fp and fp.status == "BLOCKED":
                print_success("✅ Status updated successfully")
            else:
                print_error("Status update failed")
                return False
        else:
            print_error("Update function returned False")
            return False
        
        # Test clear user fingerprints
        cleared = clear_user_fingerprints("db_test_user")
        if cleared > 0:
            print_success(f"✅ Cleared {cleared} fingerprint(s) for user")
        else:
            print_warning("No fingerprints cleared")
        
        # Test delete
        deleted = delete_fingerprint("fp-db-test-001")
        if deleted:
            fp_after = get_fingerprint_by_id("fp-db-test-001")
            if fp_after is None:
                print_success("✅ Fingerprint deleted successfully")
                return True
            else:
                print_error("Fingerprint still exists after delete")
                return False
        else:
            print_error("Delete function returned False")
            return False
    except Exception as e:
        print_error(f"Database operations test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_test_data():
    """Clean up test data"""
    print_header("Cleanup: Removing Test Data")
    try:
        from storage import get_fingerprints, delete_fingerprint
        
        all_fps = get_fingerprints()
        test_fps = [fp for fp in all_fps if fp.fingerprint_id.startswith("fp-test-") or 
                   fp.fingerprint_id.startswith("fp-multi-") or
                   fp.fingerprint_id.startswith("fp-blocked-") or
                   fp.fingerprint_id.startswith("fp-db-test-")]
        
        deleted_count = 0
        for fp in test_fps:
            if delete_fingerprint(fp.fingerprint_id):
                deleted_count += 1
        
        print_info(f"Deleted {deleted_count} test fingerprints")
    except Exception as e:
        print_warning(f"Cleanup warning: {e}")

def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         PredictIQ - Feature Testing Suite                 ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(Colors.ENDC)
    
    results = []
    
    # Run all tests
    results.append(("Database Initialization", test_database_initialization()))
    results.append(("Basic Fingerprint Storage", test_basic_fingerprint_storage()))
    results.append(("Multi-Account Detection", test_multi_account_detection()))
    results.append(("Browser-Hopping Detection", test_browser_hopping_detection()))
    results.append(("Similar-Behavior Detection", test_similar_behavior_detection()))
    results.append(("Risk Score Boost", test_risk_score_boost()))
    results.append(("Database Operations", test_database_operations()))
    
    # Print summary
    print_header("Test Results Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Colors.OKGREEN}✅ PASS{Colors.ENDC}" if result else f"{Colors.FAIL}❌ FAIL{Colors.ENDC}"
        print(f"{status} - {test_name}")
    
    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.ENDC}\n")
    
    # Ask for cleanup
    try:
        cleanup = input("Do you want to cleanup test data? (y/n): ").lower().strip()
        if cleanup == 'y':
            cleanup_test_data()
    except:
        pass
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

