"""
اختبارات محرك تحليل التهديدات (engine.py)
"""
import unittest
import sys
import os
from datetime import datetime, timedelta

# إضافة مسار backend إلى Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import process_event, is_user_fingerprinted, calculate_behavioral_features
from models import Event, ThreatFingerprint
from storage import EVENTS_STORE, FINGERPRINTS_STORE, store_event, store_fingerprint


class TestEngine(unittest.TestCase):
    """اختبارات محرك التحليل"""
    
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
    
    def test_process_normal_event(self):
        """اختبار معالجة حدث عادي (لا يجب إنشاء بصمة)"""
        event = Event(
            event_type="login_attempt",
            user_id="user-normal",
            device_id="device-1",
            timestamp1=datetime.now()
        )
        
        fingerprint = process_event(event)
        
        # حدث عادي لا يجب أن ينشئ بصمة
        self.assertIsNone(fingerprint)
        self.assertEqual(len(FINGERPRINTS_STORE), 0)
    
    def test_process_rapid_events(self):
        """اختبار معالجة أحداث سريعة (يجب إنشاء بصمة)"""
        # التأكد من أن التخزين فارغ
        self.assertEqual(len(EVENTS_STORE), 0)
        self.assertEqual(len(FINGERPRINTS_STORE), 0)
        
        # إضافة 10 أحداث سريعة (كل 0.2 ثانية = 2 ثانية إجمالي)
        base_time = datetime.now()
        events_list = []
        for i in range(10):
            event = Event(
                event_type="update_mobile_attempt",
                user_id="user-rapid",
                device_id="device-1",
                timestamp1=base_time + timedelta(seconds=i * 0.2)  # كل 0.2 ثانية
            )
            store_event(event)
            events_list.append(event)
        
        self.assertEqual(len(EVENTS_STORE), 10)
        
        # معالجة الحدث الأخير (يجب أن يحفظه أولاً)
        last_event = Event(
            event_type="update_mobile_attempt",
            user_id="user-rapid",
            device_id="device-1",
            timestamp1=base_time + timedelta(seconds=2.0)
        )
        
        # حفظ الحدث قبل المعالجة (كما يحدث في main.py)
        store_event(last_event)
        
        fingerprint = process_event(last_event)
        
        # يجب إنشاء بصمة بسبب النقرات السريعة (8+ أحداث في 3 ثوانٍ)
        # الآن لدينا 11 حدث في ~2 ثانية
        self.assertIsNotNone(fingerprint, "يجب إنشاء بصمة للأحداث السريعة")
        self.assertGreaterEqual(len(FINGERPRINTS_STORE), 1, "يجب أن تكون هناك بصمة واحدة على الأقل")
        if fingerprint:
            self.assertGreaterEqual(fingerprint.risk_score, 80, f"درجة الخطورة يجب أن تكون >= 80، لكنها {fingerprint.risk_score}")
            self.assertEqual(fingerprint.status, "ACTIVE")
    
    def test_calculate_behavioral_features(self):
        """اختبار حساب الخصائص السلوكية"""
        user_id = "user-features"
        device_id = "device-1"
        current_time = datetime.now()
        
        # إضافة أحداث متنوعة
        events = [
            Event("login_attempt", user_id, device_id, current_time - timedelta(minutes=5)),
            Event("update_mobile_attempt", user_id, device_id, current_time - timedelta(minutes=4)),
            Event("update_mobile_attempt", user_id, device_id, current_time - timedelta(minutes=3)),
            Event("view_service", user_id, device_id, current_time - timedelta(minutes=2)),
            Event("download_file", user_id, device_id, current_time - timedelta(minutes=1)),
        ]
        
        for event in events:
            store_event(event)
        
        features = calculate_behavioral_features(user_id, device_id, current_time)
        
        # التحقق من وجود الخصائص الأساسية
        self.assertIn("total_events", features)
        self.assertIn("events_per_minute", features)
        self.assertIn("update_mobile_attempt_count", features)
        
        # التحقق من القيم
        self.assertGreaterEqual(features["total_events"], 5)
    
    def test_is_user_fingerprinted(self):
        """اختبار التحقق من وجود بصمة نشطة لمستخدم"""
        # التأكد من أن التخزين فارغ
        self.assertEqual(len(FINGERPRINTS_STORE), 0)
        
        # إضافة بصمة نشطة
        fingerprint = ThreatFingerprint(
            fingerprint_id="fp-test",
            risk_score=90,
            user_id="user-blocked",
            status="ACTIVE",
            behavioral_features={}
        )
        store_fingerprint(fingerprint)
        
        self.assertEqual(len(FINGERPRINTS_STORE), 1)
        
        # التحقق من وجود بصمة نشطة
        result = is_user_fingerprinted("user-blocked")
        self.assertTrue(result)
        
        # التحقق من عدم وجود بصمة لمستخدم آخر
        result2 = is_user_fingerprinted("user-clean")
        self.assertFalse(result2)
    
    def test_is_user_fingerprinted_cleared(self):
        """اختبار أن البصمات CLEARED لا تمنع الوصول"""
        # إضافة بصمة CLEARED
        fingerprint = ThreatFingerprint(
            fingerprint_id="fp-cleared",
            risk_score=90,
            user_id="user-cleared",
            status="CLEARED",
            behavioral_features={}
        )
        store_fingerprint(fingerprint)
        
        # CLEARED لا يجب أن تمنع الوصول
        result = is_user_fingerprinted("user-cleared")
        self.assertFalse(result)
    
    def test_high_volume_attack(self):
        """اختبار هجوم حجم عالي"""
        user_id = "user-high-volume"
        device_id = "device-1"
        base_time = datetime.now()
        
        # إضافة 30 حدث في دقيقة واحدة
        for i in range(30):
            event = Event(
                event_type="view_service",
                user_id=user_id,
                device_id=device_id,
                timestamp1=base_time - timedelta(seconds=60 - i)
            )
            store_event(event)
        
        # معالجة حدث جديد
        new_event = Event(
            event_type="view_service",
            user_id=user_id,
            device_id=device_id,
            timestamp1=base_time
        )
        
        fingerprint = process_event(new_event)
        
        # يجب إنشاء بصمة بسبب الحجم العالي
        self.assertIsNotNone(fingerprint)
        self.assertGreaterEqual(fingerprint.risk_score, 80)


if __name__ == '__main__':
    unittest.main()

