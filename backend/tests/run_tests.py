"""
سكريبت تشغيل جميع الاختبارات
"""
import unittest
import sys
import os

# إضافة مسار backend إلى Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_all_tests():
    """تشغيل جميع الاختبارات"""
    # اكتشاف جميع ملفات الاختبار
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # إضافة جميع الاختبارات
    suite.addTests(loader.discover(os.path.dirname(__file__), pattern='test_*.py'))
    
    # تشغيل الاختبارات
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # إرجاع نتيجة الاختبارات
    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    import io
    
    # إصلاح مشكلة Unicode في Windows console
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 70)
    print("بدء تشغيل اختبارات Digital Threat Fingerprint")
    print("=" * 70)
    print()
    
    success = run_all_tests()
    
    print()
    print("=" * 70)
    if success:
        print("جميع الاختبارات نجحت!")
    else:
        print("بعض الاختبارات فشلت!")
    print("=" * 70)
    
    sys.exit(0 if success else 1)

