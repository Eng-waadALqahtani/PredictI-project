# شرح نظام حجب البصمات - الملفات المسؤولة

## الملفات الرئيسية المسؤولة عن الحجب:

### 1. **`backend/main.py`** - نقطة الدخول الرئيسية للحجب
   - **الدالة**: `check_and_login()` (السطر 437)
   - **المسار**: `/api/v1/check-and-login`
   - **المسؤولية**: 
     - استقبال طلبات التحقق من الحجب
     - استدعاء `is_user_fingerprinted()` للتحقق
     - إرجاع 403 إذا كان المستخدم محجوباً
     - إرجاع 200 إذا كان مسموحاً

### 2. **`backend/engine.py`** - منطق التحقق من الحجب
   - **الدالة**: `is_user_fingerprinted(user_id)` (السطر 420)
   - **المسؤولية**:
     - قراءة البصمات من قاعدة البيانات
     - التحقق من وجود بصمة بـ `status = "ACTIVE"` و `risk_score >= 80`
     - إرجاع `True` إذا كان محجوباً، `False` إذا لم يكن

### 3. **`backend/storage.py`** - عمليات قاعدة البيانات
   - **الدوال**:
     - `get_fingerprints()` - جلب جميع البصمات
     - `update_fingerprint_status()` - تحديث حالة البصمة (ACTIVE/BLOCKED/CLEARED)
     - `clear_user_fingerprints()` - إزالة الحجب عن مستخدم

### 4. **`backend/db.py`** - قاعدة البيانات
   - **النموذج**: `FingerprintDB`
   - **الحقول المهمة**:
     - `risk_score` - درجة الخطورة (0-100)
     - `status` - الحالة (ACTIVE/BLOCKED/CLEARED)

## تدفق عملية الحجب:

```
1. المستخدم يحاول تسجيل الدخول
   ↓
2. Frontend يرسل POST إلى /api/v1/check-and-login
   ↓
3. main.py → check_and_login()
   ↓
4. engine.py → is_user_fingerprinted(user_id)
   ↓
5. storage.py → get_fingerprints() (من قاعدة البيانات)
   ↓
6. التحقق: risk_score >= 80 AND status = "ACTIVE"
   ↓
7. إذا True → إرجاع 403 (محجوب)
   إذا False → إرجاع 200 (مسموح)
```

## الكود الرئيسي:

### في `main.py`:
```python
@app.route('/api/v1/check-and-login', methods=['POST'])
def check_and_login():
    user_id = data.get('user_id')
    is_fingerprinted = is_user_fingerprinted(user_id)
    
    if is_fingerprinted:
        return jsonify({"status": "blocked"}), 403
    else:
        return jsonify({"status": "ok", "allowed": True}), 200
```

### في `engine.py`:
```python
def is_user_fingerprinted(user_id: str) -> bool:
    db_fingerprints = session.query(FingerprintDB).filter(
        FingerprintDB.user_id == user_id,
        FingerprintDB.status == "ACTIVE",
        FingerprintDB.risk_score >= RISK_SCORE_BLOCKING_THRESHOLD  # 80
    ).all()
    
    return len(db_fingerprints) > 0
```

## ملاحظات مهمة:

1. **الملف الرئيسي**: `backend/main.py` - يحتوي على API endpoint للحجب
2. **المنطق**: `backend/engine.py` - يحتوي على دالة التحقق
3. **قاعدة البيانات**: `backend/storage.py` و `backend/db.py` - تخزين واسترجاع البصمات
4. **الحد**: `RISK_SCORE_BLOCKING_THRESHOLD = 80` في `engine.py`

