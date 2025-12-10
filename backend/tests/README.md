# 🧪 اختبارات Backend

## تشغيل الاختبارات

### تشغيل جميع الاختبارات:
```bash
cd backend
.\venv\Scripts\python.exe tests\run_tests.py
```

### تشغيل اختبارات محددة:
```bash
# اختبارات التخزين
.\venv\Scripts\python.exe -m unittest tests.test_storage

# اختبارات المحرك
.\venv\Scripts\python.exe -m unittest tests.test_engine

# اختبارات API
.\venv\Scripts\python.exe -m unittest tests.test_api
```

## الملفات

- `test_storage.py` - اختبارات نظام التخزين
- `test_engine.py` - اختبارات محرك التحليل
- `test_api.py` - اختبارات API Endpoints
- `run_tests.py` - سكريبت تشغيل جميع الاختبارات

