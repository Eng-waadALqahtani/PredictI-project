# دليل اختبار خاصية VPN / القفزة الجغرافية (Geographic Jump Detection)

## نظرة عامة

نظام PredictAI يكتشف تلقائياً استخدام VPN أو تبديل المواقع الجغرافية بسرعة مشبوهة من خلال:

1. **التنقل المستحيل (Impossible Travel)**: انتقال المستخدم بين مدن بعيدة بسرعة أكبر من 900 كم/ساعة
2. **مواقع متعددة في وقت قصير**: ظهور المستخدم في 3+ مواقع مختلفة خلال 30 دقيقة
3. **تبديل IP متعدد**: استخدام 3+ عناوين IP مختلفة خلال 30 دقيقة

---

## طريقة الاختبار

### الطريقة 1: اختبار عبر المتصفح (Manual Testing)

#### خطوات الاختبار:

1. **افتح صفحة Absher أو Tawakkalna**
   ```
   http://localhost:5000/absher-login.html
   أو
   http://localhost:5000/tawakkalna-login.html
   ```

2. **افتح Developer Console (F12)**

3. **قم بإرسال events من مواقع مختلفة:**

   **Event 1 - من الرياض:**
   ```javascript
   sendEvent('login_attempt', null, {
       page: 'absher',
       location: 'Riyadh',
       ip_address: '192.168.1.100'
   });
   ```

   **Event 2 - من جدة (بعد 5 دقائق):**
   ```javascript
   setTimeout(() => {
       sendEvent('view_service', 'vehicle_authorization', {
           page: 'absher',
           location: 'Jeddah',
           ip_address: '192.168.1.101'
       });
   }, 300000); // 5 دقائق
   ```

   **Event 3 - من الدمام (بعد 10 دقائق):**
   ```javascript
   setTimeout(() => {
       sendEvent('download_file', 'national_id', {
           page: 'absher',
           location: 'Dammam',
           ip_address: '192.168.1.102'
       });
   }, 600000); // 10 دقائق
   ```

4. **راقب الـ Console** - يجب أن ترى:
   ```
   🚨 [GEOGRAPHIC JUMP - MULTIPLE LOCATIONS] Geographic jump attack: user appeared in 3 different locations...
   ```

5. **تحقق من Dashboard** - يجب أن ترى بصمة جديدة بـ `risk_score >= 85` مع `geographic_jump_detected: true`

---

### الطريقة 2: اختبار سريع (Rapid Testing)

لاختبار أسرع، أرسل 3 events متتالية من مواقع مختلفة:

```javascript
// في Console المتصفح

const testUserId = 'user-8456123848'; // أو أي user_id
const apiBase = 'http://localhost:5000';

async function testVPNDetection() {
    const locations = ['Riyadh', 'Jeddah', 'Dammam'];
    const ips = ['192.168.1.100', '192.168.1.101', '192.168.1.102'];
    
    for (let i = 0; i < 3; i++) {
        const response = await fetch(`${apiBase}/api/v1/event`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                event_type: 'login_attempt',
                user_id: testUserId,
                device_id: 'device-demo-01',
                location: locations[i],
                ip_address: ips[i],
                timestamp1: new Date().toISOString()
            })
        });
        
        console.log(`Event ${i+1} from ${locations[i]}:`, await response.json());
        await new Promise(resolve => setTimeout(resolve, 1000)); // انتظر ثانية واحدة
    }
    
    console.log('✅ Test completed - Check dashboard for geographic jump detection');
}

testVPNDetection();
```

---

### الطريقة 3: اختبار التنقل المستحيل (Impossible Travel)

لاختبار التنقل المستحيل (سرعة > 900 كم/ساعة):

```javascript
// Event 1: من الرياض في الساعة 10:00
const event1 = {
    event_type: 'login_attempt',
    user_id: 'user-8456123848',
    device_id: 'device-demo-01',
    location: 'Riyadh',
    ip_address: '192.168.1.100',
    timestamp1: new Date('2025-01-01T10:00:00Z').toISOString()
};

// Event 2: من أبها في الساعة 10:05 (بعد 5 دقائق فقط)
// المسافة بين الرياض وأبها: ~950 كم
// السرعة المطلوبة: ~11,400 كم/ساعة (مستحيلة!)
const event2 = {
    event_type: 'download_file',
    user_id: 'user-8456123848',
    device_id: 'device-demo-01',
    location: 'Abha',
    ip_address: '192.168.1.101',
    timestamp1: new Date('2025-01-01T10:05:00Z').toISOString() // 5 دقائق بعد event1
};

// أرسل Events
fetch('http://localhost:5000/api/v1/event', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(event1)
}).then(r => r.json()).then(console.log);

setTimeout(() => {
    fetch('http://localhost:5000/api/v1/event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(event2)
    }).then(r => r.json()).then(console.log);
}, 2000);
```

**النتيجة المتوقعة:**
```
🚨 [GEOGRAPHIC JUMP - IMPOSSIBLE TRAVEL] Impossible travel: moved 950.xx km from Riyadh to Abha in 300s (speed = 11400.xx km/h)
```

---

## الاختبار التلقائي (Automated Test Script)

يمكنك استخدام السكريبت التالي لاختبار تلقائي:

```javascript
// test_vpn_detection.js
// تشغيله في Console المتصفح

async function testGeographicJump() {
    const apiBase = window.API_BASE || 'http://localhost:5000';
    const userId = 'user-8456123848';
    const deviceId = 'device-demo-01';
    
    console.log('🧪 Starting VPN/Geographic Jump Test...\n');
    
    const testCases = [
        { location: 'Riyadh', ip: '192.168.1.100', event: 'login_attempt' },
        { location: 'Jeddah', ip: '192.168.1.101', event: 'view_service', service: 'vehicle_authorization' },
        { location: 'Dammam', ip: '192.168.1.102', event: 'download_file', service: 'national_id' }
    ];
    
    for (let i = 0; i < testCases.length; i++) {
        const test = testCases[i];
        const payload = {
            event_type: test.event,
            user_id: userId,
            device_id: deviceId,
            location: test.location,
            ip_address: test.ip,
            timestamp1: new Date().toISOString()
        };
        
        if (test.service) {
            payload.service_name = test.service;
        }
        
        try {
            const response = await fetch(`${apiBase}/api/v1/event`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            console.log(`✅ Event ${i+1}: ${test.location} (${test.ip}) - Risk: ${result.risk_score || 'N/A'}`);
            
            // انتظر ثانية واحدة قبل إرسال Event التالي
            if (i < testCases.length - 1) {
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
        } catch (error) {
            console.error(`❌ Error sending event ${i+1}:`, error);
        }
    }
    
    console.log('\n✅ Test completed!');
    console.log('📊 Check dashboard at: http://localhost:5000/dashboard.html');
    console.log('🔍 Look for fingerprint with geographic_jump_detected: true');
}

// تشغيل الاختبار
testGeographicJump();
```

---

## التحقق من النتائج

### 1. Dashboard
افتح: `http://localhost:5000/dashboard.html`

ابحث عن:
- بصمة جديدة بـ `risk_score >= 85`
- في `behavioral_features`: `geographic_jump_detected: true`
- `ip_address` مختلف لكل event

### 2. Backend Console
راقب الـ terminal حيث يعمل الخادم:
```
🚨 [GEOGRAPHIC JUMP - MULTIPLE LOCATIONS] Geographic jump attack: user appeared in 3 different locations in 30 minutes...
🚨 [GEOGRAPHIC JUMP] Risk score boosted to 85
✅ [FINGERPRINT CREATED] ID: fp-xxx, Risk: 85
```

### 3. Database
```bash
python backend/view_database.py
```

ابحث عن بصمات تحتوي على:
- `geographic_jump_detected: true`
- `risk_score >= 85`
- `ip_address` متعددة مختلفة

---

## سيناريوهات الاختبار المختلفة

### السيناريو 1: VPN Hopping (تبديل VPN سريع)
- 3+ مواقع مختلفة في 5 دقائق
- **المتوقع**: كشف فوري + `risk_score >= 85`

### السيناريو 2: Impossible Travel
- الرياض → أبها في 5 دقائق (سرعة > 900 كم/ساعة)
- **المتوقع**: كشف "Impossible Travel" + `risk_score >= 85`

### السيناريو 3: Multiple IPs (تبديل IP متعدد)
- 3+ IPs مختلفة في 30 دقيقة
- **المتوقع**: كشف "IP Switching" + `risk_score >= 85`

### السيناريو 4: Normal Travel (سفر طبيعي)
- الرياض → جدة في ساعتين (سرعة < 900 كم/ساعة)
- **المتوقع**: لا كشف (سلوك طبيعي)

---

## ملاحظات مهمة

1. **الحد الزمني**: النظام يراقب آخر 30 دقيقة فقط
2. **الحد الأدنى**: يحتاج 3+ مواقع أو IPs مختلفة
3. **السرعة القصوى**: 900 كم/ساعة (يمكن تعديلها في `engine.py`)
4. **التأثير على Risk Score**: يرفع `risk_score` إلى 85 على الأقل

---

## تعديل إعدادات الكشف

إذا أردت تغيير الحدود، عدّل في `backend/engine.py`:

```python
# خط 305: تغيير حد السرعة
if speed_kmh > 900:  # غيرها إلى 500 أو 1000 حسب الحاجة

# خط 335: تغيير عدد المواقع المطلوبة
if len(unique_locations) >= 3:  # غيرها إلى 2 أو 4

# خط 345: تغيير عدد IPs المطلوبة
if len(unique_ips) >= 3:  # غيرها إلى 2 أو 4

# خط 318: تغيير النافذة الزمنية (30 دقيقة)
thirty_minutes_ago = current_time - timedelta(minutes=30)  # غيرها إلى 15 أو 60
```

---

## استكشاف الأخطاء

### المشكلة: لا يتم الكشف عن VPN
**الحلول:**
1. تأكد من إرسال `location` و `ip_address` في كل event
2. تأكد من أن المواقع مختلفة تماماً (Riyadh, Jeddah, Dammam)
3. تأكد من أن الأحداث في نافذة 30 دقيقة

### المشكلة: الكشف لا يرفع Risk Score
**الحلول:**
1. تحقق من logs في backend console
2. تأكد من أن `detect_geographic_jump` يُرجع reason (ليست None)
3. تحقق من أن `process_event` يستدعي `detect_geographic_jump`

---

## أمثلة JSON للـ API

```json
{
    "event_type": "login_attempt",
    "user_id": "user-8456123848",
    "device_id": "device-demo-01",
    "location": "Riyadh",
    "ip_address": "192.168.1.100",
    "timestamp1": "2025-01-01T10:00:00Z"
}
```

```json
{
    "event_type": "download_file",
    "user_id": "user-8456123848",
    "device_id": "device-demo-01",
    "location": "Jeddah",
    "ip_address": "192.168.1.101",
    "service_name": "national_id",
    "timestamp1": "2025-01-01T10:05:00Z"
}
```

---

## الدعم

إذا واجهت مشاكل، تحقق من:
- `backend/engine.py` - دالة `detect_geographic_jump()`
- `backend/main.py` - endpoint `/api/v1/event`
- Backend console logs

