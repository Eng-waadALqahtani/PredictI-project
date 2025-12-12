# 🔧 دليل تثبيت Git على Windows

## الطريقة 1: تثبيت Git (موصى به)

### الخطوات:

1. **تحميل Git for Windows**
   - اذهب إلى: https://git-scm.com/download/win
   - أو استخدم الرابط المباشر: https://github.com/git-for-windows/git/releases/latest

2. **تثبيت Git**
   - شغّل ملف التثبيت `.exe`
   - اختر "Next" في جميع الخطوات (الإعدادات الافتراضية جيدة)
   - تأكد من اختيار "Add Git to PATH" أثناء التثبيت

3. **إعادة تشغيل PowerShell**
   - أغلق PowerShell الحالي
   - افتح PowerShell جديد
   - اكتب: `git --version` للتحقق من التثبيت

4. **إعداد Git (للمرة الأولى)**
   ```powershell
   git config --global user.name "Your Name"
   git config --global user.email "your.email@example.com"
   ```

5. **الآن يمكنك استخدام Git**
   ```powershell
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin main
   ```

---

## الطريقة 2: استخدام GitHub Desktop (أسهل)

1. **تحميل GitHub Desktop**
   - اذهب إلى: https://desktop.github.com/
   - شغّل التثبيت

2. **ربط حساب GitHub**
   - سجّل الدخول بحساب GitHub

3. **إنشاء مستودع جديد**
   - اضغط "File" → "New Repository"
   - اختر المجلد: `C:\Users\waaad\OneDrive - ek.com.sa\Documents\hakathoon`
   - اضغط "Create Repository"

4. **Commit و Push**
   - اضغط "Commit to main"
   - اضغط "Push origin"

---

## الطريقة 3: رفع الملفات مباشرة إلى GitHub (بدون Git)

1. **اذهب إلى GitHub**
   - https://github.com/new
   - أنشئ مستودع جديد

2. **ارفع الملفات**
   - اضغط "uploading an existing file"
   - اسحب وأفلت الملفات
   - اضغط "Commit changes"

---

## الطريقة 4: استخدام ZIP للنشر على Render مباشرة

يمكنك إنشاء ملف ZIP ورفعه مباشرة إلى Render (بدون GitHub):

1. **إنشاء ZIP**
   - اضغط بزر الماوس الأيمن على مجلد `hakathoon`
   - اختر "Send to" → "Compressed (zipped) folder"

2. **النشر على Render**
   - اذهب إلى Render Dashboard
   - اختر "Manual Deploy"
   - ارفع ملف ZIP

---

## ✅ بعد تثبيت Git

بعد تثبيت Git، استخدم هذه الأوامر:

```powershell
# الانتقال إلى مجلد المشروع
cd "C:\Users\waaad\OneDrive - ek.com.sa\Documents\hakathoon"

# إضافة جميع الملفات
git add .

# Commit
git commit -m "Prepare for Render deployment"

# Push إلى GitHub
git push origin main
```

---

## 🆘 حل المشاكل

### إذا ظهرت رسالة "git is not recognized":

1. **تحقق من PATH**
   - افتح "Environment Variables"
   - تأكد من وجود `C:\Program Files\Git\cmd` في PATH

2. **أعد تشغيل PowerShell**
   - أغلق PowerShell تماماً
   - افتح PowerShell جديد

3. **تحقق من التثبيت**
   ```powershell
   git --version
   ```

---

## 📝 ملاحظات

- **Git for Windows** يتضمن Git Bash و PowerShell
- **GitHub Desktop** أسهل للمبتدئين
- يمكنك استخدام **VS Code** مع Git extension

---

**اختر الطريقة التي تناسبك!** 🚀

