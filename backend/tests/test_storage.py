"""
اختبارات نظام التخزين (storage.py)
"""
import unittest
import sys
import os
from datetime import datetime

# إضافة مسار backend إلى Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage import (
    store_event,
    get_fingerprints,
    store_fingerprint,
    update_fingerprint_status,
    clear_user_fingerprints,
    delete_fingerprint,
    get_fingerprint_by_id,
    EVENTS_STORE,
    FINGERPRINTS_STORE
)
from models import Event, ThreatFingerprint


class TestStorage(unittest.TestCase):
    """اختبارات نظام التخزين"""
    
    def setUp(self):
        """تهيئة قبل كل اختبار"""
        # مسح التخزين قبل كل اختبار
        EVENTS_STORE[:] = []
        FINGERPRINTS_STORE[:] = []
    
    def tearDown(self):
        """تنظيف بعد كل اختبار"""
        # التأكد من مسح التخزين بعد كل اختبار
        EVENTS_STORE[:] = []
        FINGERPRINTS_STORE[:] = []
    
    def test_store_event(self):
        """اختبار حفظ حدث"""
        event = Event(
            event_type="login_attempt",
            user_id="user-123",
            device_id="device-456",
            timestamp1=datetime.now()
        )
        
        store_event(event)
        
        self.assertEqual(len(EVENTS_STORE), 1)
        self.assertEqual(EVENTS_STORE[0].event_type, "login_attempt")
        self.assertEqual(EVENTS_STORE[0].user_id, "user-123")
    
    def test_store_fingerprint(self):
        """اختبار حفظ بصمة"""
        # التأكد من أن التخزين فارغ
        initial_count = len(FINGERPRINTS_STORE)
        self.assertEqual(initial_count, 0, f"التخزين يجب أن يكون فارغاً، لكنه يحتوي على {initial_count} بصمة")
        
        fingerprint = ThreatFingerprint(
            fingerprint_id="fp-test-001",
            risk_score=85,
            user_id="user-123",
            status="ACTIVE",
            behavioral_features={"total_events": 20}
        )
        
        # حفظ البصمة
        store_fingerprint(fingerprint)
        
        # التحقق من الحفظ
        after_store_count = len(FINGERPRINTS_STORE)
        self.assertEqual(after_store_count, 1, f"يجب أن تكون هناك بصمة واحدة بعد الحفظ، لكن هناك {after_store_count}")
        
        # التحقق من محتوى البصمة
        stored_fp = FINGERPRINTS_STORE[0]
        self.assertEqual(stored_fp.fingerprint_id, "fp-test-001")
        self.assertEqual(stored_fp.risk_score, 85)
    
    def test_get_fingerprints(self):
        """اختبار جلب البصمات"""
        # التأكد من أن التخزين فارغ
        self.assertEqual(len(FINGERPRINTS_STORE), 0)
        
        # إضافة بصمات
        fp1 = ThreatFingerprint(
            fingerprint_id="fp-001",
            risk_score=90,
            user_id="user-1",
            status="ACTIVE",
            behavioral_features={}
        )
        fp2 = ThreatFingerprint(
            fingerprint_id="fp-002",
            risk_score=70,
            user_id="user-2",
            status="CLEARED",
            behavioral_features={}
        )
        
        store_fingerprint(fp1)
        store_fingerprint(fp2)
        
        # التحقق من الحفظ
        self.assertEqual(len(FINGERPRINTS_STORE), 2)
        
        fingerprints = get_fingerprints()
        
        self.assertEqual(len(fingerprints), 2)
        # التحقق من وجود البصمات بالمعرفات
        fp_ids = [fp.fingerprint_id for fp in fingerprints]
        self.assertIn("fp-001", fp_ids)
        self.assertIn("fp-002", fp_ids)
    
    def test_update_fingerprint_status(self):
        """اختبار تحديث حالة البصمة"""
        # التأكد من أن التخزين فارغ
        self.assertEqual(len(FINGERPRINTS_STORE), 0)
        
        fingerprint = ThreatFingerprint(
            fingerprint_id="fp-update-test",
            risk_score=85,
            user_id="user-123",
            status="ACTIVE",
            behavioral_features={}
        )
        
        store_fingerprint(fingerprint)
        self.assertEqual(len(FINGERPRINTS_STORE), 1)
        
        # تحديث الحالة
        result = update_fingerprint_status("fp-update-test", "BLOCKED")
        
        self.assertTrue(result)
        # البحث عن البصمة بالمعرف
        updated_fp = get_fingerprint_by_id("fp-update-test")
        self.assertIsNotNone(updated_fp)
        self.assertEqual(updated_fp.status, "BLOCKED")
    
    def test_update_nonexistent_fingerprint(self):
        """اختبار تحديث بصمة غير موجودة"""
        result = update_fingerprint_status("fp-nonexistent", "BLOCKED")
        self.assertFalse(result)
    
    def test_clear_user_fingerprints(self):
        """اختبار مسح بصمات مستخدم"""
        # التأكد من أن التخزين فارغ
        self.assertEqual(len(FINGERPRINTS_STORE), 0)
        
        # إضافة بصمات لنفس المستخدم
        fp1 = ThreatFingerprint(
            fingerprint_id="fp-1",
            risk_score=90,
            user_id="user-test",
            status="ACTIVE",
            behavioral_features={}
        )
        fp2 = ThreatFingerprint(
            fingerprint_id="fp-2",
            risk_score=85,
            user_id="user-test",
            status="ACTIVE",
            behavioral_features={}
        )
        fp3 = ThreatFingerprint(
            fingerprint_id="fp-3",
            risk_score=80,
            user_id="user-other",
            status="ACTIVE",
            behavioral_features={}
        )
        
        store_fingerprint(fp1)
        store_fingerprint(fp2)
        store_fingerprint(fp3)
        
        self.assertEqual(len(FINGERPRINTS_STORE), 3)
        
        # مسح بصمات user-test
        cleared_count = clear_user_fingerprints("user-test")
        
        self.assertEqual(cleared_count, 2)
        self.assertEqual(len(FINGERPRINTS_STORE), 3)  # لا يزال fp3 موجود
        
        # التحقق من تغيير الحالة
        fp1_updated = get_fingerprint_by_id("fp-1")
        fp2_updated = get_fingerprint_by_id("fp-2")
        fp3_updated = get_fingerprint_by_id("fp-3")
        
        self.assertIsNotNone(fp1_updated)
        self.assertEqual(fp1_updated.status, "CLEARED")
        self.assertIsNotNone(fp2_updated)
        self.assertEqual(fp2_updated.status, "CLEARED")
        self.assertIsNotNone(fp3_updated)
        self.assertEqual(fp3_updated.status, "ACTIVE")  # لم تتغير
    
    def test_delete_fingerprint(self):
        """اختبار حذف بصمة"""
        # التأكد من أن التخزين فارغ
        self.assertEqual(len(FINGERPRINTS_STORE), 0)
        
        fingerprint = ThreatFingerprint(
            fingerprint_id="fp-delete-test",
            risk_score=85,
            user_id="user-123",
            status="ACTIVE",
            behavioral_features={}
        )
        
        store_fingerprint(fingerprint)
        self.assertEqual(len(FINGERPRINTS_STORE), 1)
        
        # حذف البصمة
        result = delete_fingerprint("fp-delete-test")
        
        self.assertTrue(result)
        self.assertEqual(len(FINGERPRINTS_STORE), 0)
        
        # التحقق من عدم وجود البصمة
        deleted_fp = get_fingerprint_by_id("fp-delete-test")
        self.assertIsNone(deleted_fp)
    
    def test_delete_nonexistent_fingerprint(self):
        """اختبار حذف بصمة غير موجودة"""
        result = delete_fingerprint("fp-nonexistent")
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()

