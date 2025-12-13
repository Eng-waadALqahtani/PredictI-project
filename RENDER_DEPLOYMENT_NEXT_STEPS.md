# 🚀 خطوات النشر على Render

## ✅ تم رفع المشروع إلى GitHub بنجاح!

المشروع الآن متاح على:
```
https://github.com/Eng-waadALqahtani/PredictI-project
```

---

## 📋 الخطوات التالية: النشر على Render

### 1. تسجيل الدخول إلى Render

1. اذهب إلى: https://dashboard.render.com
2. سجّل الدخول بحسابك (أو أنشئ حساب جديد)

---

### 2. ربط GitHub بـ Render

1. في Render Dashboard، اضغط **"New +"** في الأعلى
2. اختر **"Web Service"**
3. اضغط **"Connect GitHub"** أو **"Connect account"**
4. سجّل الدخول بحساب GitHub
5. امنح Render صلاحية الوصول إلى المستودعات
6. اختر المستودع: **`Eng-waadALqahtani/PredictI-project`**

---

### 3. إعدادات الخدمة

Render سيكتشف `render.yaml` تلقائياً، لكن تأكد من:

- **Name**: `predictai-backend` (أو أي اسم تريده)
- **Region**: اختر الأقرب إليك
- **Branch**: `main`
- **Root Directory**: اتركه فارغاً (أو `./`)
- **Environment**: `Python 3`
- **Build Command**: سيتم اكتشافه من `render.yaml`
- **Start Command**: `python backend/main.py` (سيتم اكتشافه من `render.yaml`)

---

### 4. متغيرات البيئة (Environment Variables)

في قسم **"Environment"**، أضف:

- **PYTHON_VERSION**: `3.10`

(هذا موجود في `render.yaml`، لكن يمكن إضافته يدوياً أيضاً)

---

### 5. إنشاء الخدمة

1. اضغط **"Create Web Service"**
2. Render سيبدأ في:
   - تثبيت التبعيات من `requirements.txt`
   - بناء المشروع
   - تشغيل السيرفر

---

### 6. انتظار النشر

- العملية قد تستغرق 5-10 دقائق
- راقب السجلات (Logs) للتأكد من عدم وجود أخطاء
- عند النجاح، ستحصل على رابط مثل:
  ```
  https://predictai-backend.onrender.com
  ```

---

## ✅ التحقق من النشر

### 1. اختبار API

افتح المتصفح واذهب إلى:
```
https://predictai-backend.onrender.com/api/v1/fingerprints
```

يجب أن ترى:
```json
[]
```

### 2. اختبار Health Check

```
https://predictai-backend.onrender.com/health
```

يجب أن ترى:
```json
{"status": "healthy"}
```

---

## 🔧 تحديث Frontend

بعد الحصول على رابط Render، يجب تحديث `frontend/js/events.js`:

1. افتح `frontend/js/events.js`
2. تأكد من أن `API_BASE` يحتوي على:
   ```javascript
   const API_BASE = (window.location.hostname.includes("render"))
     ? "https://predictai-backend.onrender.com"
     : "http://localhost:5000";
   ```

3. إذا كان الرابط مختلفاً، استبدل `predictai-backend.onrender.com` بالرابط الصحيح

---

## 📝 تحديث GitHub بعد التغييرات

إذا قمت بأي تغييرات:

```powershell
git add .
git commit -m "Update API URL"
git push
```

Render سيعيد النشر تلقائياً!

---

## 🆘 حل المشاكل الشائعة

### المشكلة: Build Failed

**الحل:**
- تحقق من `requirements.txt` - تأكد من وجود جميع المكتبات
- تحقق من السجلات (Logs) في Render Dashboard
- تأكد من أن `PYTHON_VERSION` مضبوط على `3.10`

### المشكلة: Service Crashes

**الحل:**
- تحقق من السجلات (Logs)
- تأكد من أن `main.py` يستخدم `PORT` environment variable:
  ```python
  port = int(os.environ.get("PORT", 5000))
  ```

### المشكلة: CORS Errors

**الحل:**
- تأكد من أن `main.py` يحتوي على CORS configuration
- تحقق من أن `API_BASE` في `events.js` صحيح

### المشكلة: Model File Not Found

**الحل:**
- تأكد من أن `ml/models/isoforest_absher.pkl` موجود في GitHub
- تحقق من المسار في `main.py`:
  ```python
  model_path = os.path.join(os.path.dirname(__file__), '..', 'ml', 'models', 'isoforest_absher.pkl')
  ```

---

## 📊 مراقبة الخدمة

### في Render Dashboard:

- **Logs**: عرض السجلات المباشرة
- **Metrics**: مراقبة الأداء
- **Events**: عرض الأحداث والتغييرات

---

## 🎉 تهانينا!

المشروع الآن منشور على Render وجاهز للاستخدام!

**الرابط**: `https://predictai-backend.onrender.com`

---

## 📞 الدعم

إذا واجهت أي مشاكل:
1. تحقق من السجلات في Render Dashboard
2. راجع `render.yaml` للتأكد من الإعدادات
3. تأكد من أن جميع الملفات موجودة في GitHub

---

**جاهز للنشر!** 🚀

