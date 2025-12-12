# 🚀 دليل التشغيل السريع

## المشكلة: ModuleNotFoundError: No module named 'flask'

### ✅ الحل:

يجب تفعيل البيئة الافتراضية (Virtual Environment) قبل تشغيل السيرفر.

---

## الطريقة 1: استخدام ملف الباتش (الأسهل) ⭐

**انقر نقراً مزدوجاً على:**
```
START_SERVER.bat
```

هذا الملف سيفعل البيئة تلقائياً ويشغل السيرفر.

---

## الطريقة 2: من PowerShell

### الخطوة 1: تفعيل البيئة الافتراضية
```powershell
cd "c:\Users\waaad\OneDrive - ek.com.sa\Documents\hakathoon"
.venv\Scripts\Activate.ps1
```

### الخطوة 2: تشغيل السيرفر
```powershell
cd backend
python main.py
```

---

## الطريقة 3: استخدام Python من البيئة مباشرة

```powershell
cd "c:\Users\waaad\OneDrive - ek.com.sa\Documents\hakathoon"
.venv\Scripts\python.exe backend\main.py
```

---

## إذا لم تعمل الطرق السابقة:

### 1. تأكد من تثبيت المكتبات:
```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. تحقق من وجود Flask:
```powershell
.venv\Scripts\python.exe -m pip list | Select-String flask
```

يجب أن ترى:
```
Flask           3.1.2
flask-cors      6.0.1
```

---

## ✅ بعد تشغيل السيرفر بنجاح:

افتح المتصفح واذهب إلى:
- **Health Portal**: http://localhost:5000
- **Dashboard**: http://localhost:5000/dashboard.html

---

## 🔧 استكشاف الأخطاء

### خطأ: "cannot be loaded because running scripts is disabled"
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### خطأ: "No module named 'flask'"
- تأكد من تفعيل البيئة الافتراضية
- أو استخدم: `.venv\Scripts\python.exe` مباشرة

---

**جاهز! 🎉**

