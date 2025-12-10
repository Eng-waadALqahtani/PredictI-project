"""
اختبارات API Endpoints (main.py)
"""
import unittest
import sys
import os
import json
from datetime import datetime

# إضافة مسار backend إلى Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from storage import EVENTS_STORE, FINGERPRINTS_STORE, store_fingerprint
from models import ThreatFingerprint


class TestAPI(unittest.TestCase):
    """اختبارات API Endpoints"""
    
    def setUp(self):
        """تهيئة قبل كل اختبار"""
        self.app = app.test_client()
        self.app.testing = True
        # مسح التخزين قبل كل اختبار
        EVENTS_STORE[:] = []
        FINGERPRINTS_STORE[:] = []
    
    def tearDown(self):
        """تنظيف بعد كل اختبار"""
        # التأكد من مسح التخزين بعد كل اختبار
        EVENTS_STORE[:] = []
        FINGERPRINTS_STORE[:] = []
    
    def test_post_event(self):
        """اختبار POST /api/v1/event"""
        event_data = {
            "event_type": "login_attempt",
            "user_id": "user-api-test",
            "device_id": "device-api-test",
            "timestamp1": datetime.now().isoformat(),
            "platform": "tawakkalna"
        }
        
        response = self.app.post(
            '/api/v1/event',
            data=json.dumps(event_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "ok")
    
    def test_get_fingerprints(self):
        """اختبار GET /api/v1/fingerprints"""
        # إضافة بصمة للاختبار
        fingerprint = ThreatFingerprint(
            fingerprint_id="fp-api-test",
            risk_score=85,
            user_id="user-api-test",
            status="ACTIVE",
            behavioral_features={"total_events": 10}
        )
        store_fingerprint(fingerprint)
        
        response = self.app.get('/api/v1/fingerprints')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
    
    def test_check_and_login_allowed(self):
        """اختبار POST /api/v1/check-and-login (مسموح)"""
        data = {
            "user_id": "user-clean"
        }
        
        response = self.app.post(
            '/api/v1/check-and-login',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["allowed"])
    
    def test_check_and_login_blocked(self):
        """اختبار POST /api/v1/check-and-login (محجوب)"""
        # إضافة بصمة نشطة
        fingerprint = ThreatFingerprint(
            fingerprint_id="fp-block-test",
            risk_score=90,
            user_id="user-blocked",
            status="ACTIVE",
            behavioral_features={}
        )
        store_fingerprint(fingerprint)
        
        data = {
            "user_id": "user-blocked"
        }
        
        response = self.app.post(
            '/api/v1/check-and-login',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
        result = json.loads(response.data)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["allowed"])
    
    def test_confirm_threat(self):
        """اختبار POST /api/v1/confirm-threat"""
        # إضافة بصمة
        fingerprint = ThreatFingerprint(
            fingerprint_id="fp-confirm-test",
            risk_score=85,
            user_id="user-test",
            status="ACTIVE",
            behavioral_features={}
        )
        store_fingerprint(fingerprint)
        
        data = {
            "fingerprint_id": "fp-confirm-test"
        }
        
        response = self.app.post(
            '/api/v1/confirm-threat',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result["status"], "ok")
        
        # التحقق من تغيير الحالة
        updated_fp = next((fp for fp in FINGERPRINTS_STORE if fp.fingerprint_id == "fp-confirm-test"), None)
        self.assertIsNotNone(updated_fp)
        self.assertEqual(updated_fp.status, "BLOCKED")
    
    def test_unblock_user(self):
        """اختبار POST /api/v1/unblock-user"""
        # إضافة بصمات نشطة
        fp1 = ThreatFingerprint(
            fingerprint_id="fp-unblock-1",
            risk_score=90,
            user_id="user-unblock",
            status="ACTIVE",
            behavioral_features={}
        )
        fp2 = ThreatFingerprint(
            fingerprint_id="fp-unblock-2",
            risk_score=85,
            user_id="user-unblock",
            status="ACTIVE",
            behavioral_features={}
        )
        store_fingerprint(fp1)
        store_fingerprint(fp2)
        
        data = {
            "user_id": "user-unblock"
        }
        
        response = self.app.post(
            '/api/v1/unblock-user',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["cleared_fingerprints"], 2)
        
        # التحقق من تغيير الحالة
        for fp in FINGERPRINTS_STORE:
            if fp.user_id == "user-unblock":
                self.assertEqual(fp.status, "CLEARED")
    
    def test_delete_fingerprint(self):
        """اختبار POST /api/v1/delete-fingerprint"""
        # التأكد من أن التخزين فارغ
        self.assertEqual(len(FINGERPRINTS_STORE), 0)
        
        # إضافة بصمة
        fingerprint = ThreatFingerprint(
            fingerprint_id="fp-delete-api",
            risk_score=85,
            user_id="user-test",
            status="ACTIVE",
            behavioral_features={}
        )
        store_fingerprint(fingerprint)
        
        self.assertEqual(len(FINGERPRINTS_STORE), 1)
        
        data = {
            "fingerprint_id": "fp-delete-api"
        }
        
        response = self.app.post(
            '/api/v1/delete-fingerprint',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result["status"], "ok")
        
        # التحقق من الحذف
        self.assertEqual(len(FINGERPRINTS_STORE), 0, "يجب أن يكون التخزين فارغاً بعد الحذف")
        deleted_fp = next((fp for fp in FINGERPRINTS_STORE if fp.fingerprint_id == "fp-delete-api"), None)
        self.assertIsNone(deleted_fp)


if __name__ == '__main__':
    unittest.main()

