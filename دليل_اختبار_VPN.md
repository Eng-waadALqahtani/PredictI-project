# دليل اختبار خاصية VPN / القفزة الجغرافية

## 📋 نظرة عامة

نظام PredictAI يكتشف تلقائياً استخدام VPN أو تبديل المواقع الجغرافية بسرعة مشبوهة من خلال ثلاث طرق:

1. **التنقل المستحيل (Impossible Travel)**: انتقال المستخدم بين مدن بعيدة بسرعة أكبر من 900 كم/ساعة
2. **مواقع متعددة في وقت قصير**: ظهور المستخدم في 3+ مواقع مختلفة خلال 30 دقيقة
3. **تبديل IP متعدد**: استخدام 3+ عناوين IP مختلفة خلال 30 دقيقة

---

## 🚀 طريقة الاختبار السريعة (الأسهل)

### استخدام صفحة الاختبار المخصصة

1. **شغّل الخادم:**
   ```bash
   python backend/main.py
   ```

2. **افتح صفحة الاختبار:**
   ```
   http://localhost:5000/vpn-test.html
   ```

3. **اختر نوع الاختبار:**
   - **اختبار سريع**: يرسل 3 events من مواقع مختلفة (الرياض، جدة، الدمام)
   - **اختبار التنقل المستحيل**: يرسل event من الرياض ثم من أبها بعد 5 دقائق فقط
   - **اختبار مخصص**: اختر 3 مواقع بنفسك

4. **اضغط على زر الاختبار** وانتظر النتائج

5. **تحقق من Dashboard:**
   - اضغط على زر "فحص Dashboard"
   - أو افتح: `http://localhost:5000/dashboard.html`
   - ابحث عن بصمة جديدة بـ `risk_score >= 85` مع `geographic_jump_detected: true`

---

## 🔧 طريقة الاختبار اليدوية (Console)

### في صفحة Absher أو Tawakkalna:

1. **افتح Developer Console (F12)**

2. **أرسل events من مواقع مختلفة:**

   ```javascript
   // Event 1 - من الرياض
   sendEvent('login_attempt', null, {
       page: 'absher',
       location: 'Riyadh',
       ip_address: '192.168.1.100'
   });

   // Event 2 - من جدة (بعد ثانيتين)
   setTimeout(() => {
       sendEvent('view_service', 'vehicle_authorization', {
           page: 'absher',
           location: 'Jeddah',
           ip_address: '192.168.1.101'
       });
   }, 2000);

   // Event 3 - من الدمام (بعد 4 ثوان)
   setTimeout(() => {
       sendEvent('download_file', 'national_id', {
           page: 'absher',
           location: 'Dammam',
           ip_address: '192.168.1.102'
       });
   }, 4000);
   ```

3. **راقب Console** - يجب أن ترى:
   ```
   🚨 [GEOGRAPHIC JUMP - MULTIPLE LOCATIONS] Geographic jump attack...
   ```

---

## 📝 مثال كود للاختبار التلقائي

انسخ والصق هذا الكود في Console المتصفح:

```javascript
// اختبار VPN / القفزة الجغرافية
async function testVPN() {
    const apiBase = 'http://localhost:5000';
    const userId = 'user-8456123848';
    const deviceId = 'device-demo-01';
    
    const locations = ['Riyadh', 'Jeddah', 'Dammam'];
    const ips = ['192.168.1.100', '192.168.1.101', '192.168.1.102'];
    const events = ['login_attempt', 'view_service', 'download_file'];
    const services = [null, 'vehicle_authorization', 'national_id'];
    
    console.log('🧪 بدء اختبار VPN...');
    
    for (let i = 0; i < 3; i++) {
        const payload = {
            event_type: events[i],
            user_id: userId,
            device_id: deviceId,
            location: locations[i],
            ip_address: ips[i],
            timestamp1: new Date().toISOString()
        };
        
        if (services[i]) {
            payload.service_name = services[i];
        }
        
        try {
            const response = await fetch(`${apiBase}/api/v1/event`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            console.log(`✅ Event ${i+1} من ${locations[i]}: Risk Score = ${result.risk_score || 'N/A'}`);
            
            if (result.fingerprint_generated) {
                console.warn(`🚨 تم إنشاء بصمة تهديد! ID: ${result.fingerprint_id}`);
            }
            
            // انتظر ثانية واحدة
            if (i < 2) {
                await new Promise(r => setTimeout(r, 1000));
            }
        } catch (error) {
            console.error(`❌ خطأ في Event ${i+1}:`, error);
        }
    }
    
    console.log('✅ اكتمل الاختبار! تحقق من Dashboard');
}

// تشغيل الاختبار
testVPN();
```

---

## ✅ التحقق من النتائج

### 1. في Dashboard
- افتح: `http://localhost:5000/dashboard.html`
- ابحث عن:
  - بصمة جديدة بـ `risk_score >= 85`
  - في `behavioral_features`: `geographic_jump_detected: true`
  - `ip_address` مختلف لكل event

### 2. في Backend Console
راقب terminal الخادم - يجب أن ترى:
```
🚨 [GEOGRAPHIC JUMP - MULTIPLE LOCATIONS] Geographic jump attack: user appeared in 3 different locations...
🚨 [GEOGRAPHIC JUMP] Risk score boosted to 85
✅ [FINGERPRINT CREATED] ID: fp-xxx, Risk: 85
```

### 3. في قاعدة البيانات
```bash
python backend/view_database.py
```

ابحث عن بصمات تحتوي على:
- `geographic_jump_detected: true`
- `risk_score >= 85`
- `ip_address` متعددة مختلفة

---

## 🎯 سيناريوهات الاختبار

### السيناريو 1: VPN Hopping (تبديل VPN سريع)
- **3+ مواقع مختلفة في 5 دقائق**
- **المتوقع**: كشف فوري + `risk_score >= 85`

### السيناريو 2: Impossible Travel (تنقل مستحيل)
- **الرياض → أبها في 5 دقائق** (سرعة > 900 كم/ساعة)
- **المتوقع**: كشف "Impossible Travel" + `risk_score >= 85`

### السيناريو 3: Multiple IPs (تبديل IP متعدد)
- **3+ IPs مختلفة في 30 دقيقة**
- **المتوقع**: كشف "IP Switching" + `risk_score >= 85`

### السيناريو 4: Normal Travel (سفر طبيعي)
- **الرياض → جدة في ساعتين** (سرعة < 900 كم/ساعة)
- **المتوقع**: لا كشف (سلوك طبيعي)

---

## ⚙️ إعدادات الكشف (قابلة للتعديل)

إذا أردت تغيير الحدود، عدّل في `backend/engine.py`:

```python
# خط 305: تغيير حد السرعة (افتراضي: 900 كم/ساعة)
if speed_kmh > 900:  # غيرها إلى 500 أو 1000

# خط 335: تغيير عدد المواقع المطلوبة (افتراضي: 3)
if len(unique_locations) >= 3:  # غيرها إلى 2 أو 4

# خط 345: تغيير عدد IPs المطلوبة (افتراضي: 3)
if len(unique_ips) >= 3:  # غيرها إلى 2 أو 4

# خط 318: تغيير النافذة الزمنية (افتراضي: 30 دقيقة)
thirty_minutes_ago = current_time - timedelta(minutes=30)  # غيرها إلى 15 أو 60
```

---

## ❓ استكشاف الأخطاء

### المشكلة: لا يتم الكشف عن VPN

**الحلول:**
1. تأكد من إرسال `location` و `ip_address` في كل event
2. تأكد من أن المواقع مختلفة تماماً (Riyadh, Jeddah, Dammam)
3. تأكد من أن الأحداث في نافذة 30 دقيقة
4. تأكد من أن الخادم يعمل على `http://localhost:5000`

### المشكلة: الكشف لا يرفع Risk Score

**الحلول:**
1. تحقق من logs في backend console
2. تأكد من أن `detect_geographic_jump` يُرجع reason (ليست None)
3. تحقق من أن `process_event` يستدعي `detect_geographic_jump`

---

## 📚 المدن المتاحة

النظام يدعم المدن التالية:
- Riyadh (الرياض)
- Jeddah (جدة)
- Dammam (الدمام)
- Abha (أبها)
- Mecca (مكة)
- Medina (المدينة)
- Khobar (الخبر)
- Tabuk (تبوك)
- Buraidah (بريدة)
- وغيرها...

---

## 🔗 روابط مفيدة

- **صفحة الاختبار**: `http://localhost:5000/vpn-test.html`
- **Dashboard**: `http://localhost:5000/dashboard.html`
- **قاعدة البيانات**: `python backend/view_database.py`
- **دليل الاختبار الإنجليزي**: `VPN_TESTING_GUIDE.md`

---

## 📞 الدعم

إذا واجهت مشاكل:
1. تحقق من `backend/engine.py` - دالة `detect_geographic_jump()`
2. تحقق من `backend/main.py` - endpoint `/api/v1/event`
3. راجع Backend console logs

