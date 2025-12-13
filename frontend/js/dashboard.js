// dashboard.js - إصلاح الاتصال والتحكم اليدوي

// تحديد رابط الـ API بشكل ديناميكي أكثر دقة
const API_BASE = (function() {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    
    // إذا كنا على استضافة سحابية (Render وغيرها)
    if (hostname.includes("render") || hostname.includes("herokuapp")) {
        return ""; // استخدام نفس النطاق (Same Origin)
    }
    
    // إذا كنا محلياً، نحاول اكتشاف ما إذا كان الـ Backend يعمل على 5000
    // يمكنك تغيير هذا الرابط يدوياً إذا كان الباك اند يعمل على رابط مختلف
    return `${protocol}//${hostname}:5000`;
})();

console.log("🔌 Dashboard connected to:", API_BASE);

async function loadFingerprints() {
    const loadingMessage = document.getElementById("loading-message");
    const emptyState = document.getElementById("empty-state");
    const table = document.getElementById("fingerprints-table");
    const tbody = document.getElementById("fingerprints-tbody");
    
    // لا نخفي الجدول إذا كان هناك بيانات سابقة (لتقليل الوميض)
    if (!tbody.hasChildNodes() && loadingMessage) loadingMessage.style.display = "block";
    
    try {
        const response = await fetch(`${API_BASE}/api/v1/fingerprints`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const fingerprints = await response.json();
        
        if (loadingMessage) loadingMessage.style.display = "none";
        
        // تحديث الإحصائيات
        updateStats(fingerprints);
        
        // تفريغ الجدول لإعادة بنائه
        if (tbody) tbody.innerHTML = "";
        
        if (fingerprints.length === 0) {
            if (emptyState) emptyState.style.display = "block";
            if (table) table.style.display = "none";
        } else {
            if (emptyState) emptyState.style.display = "none";
            if (table) table.style.display = "table";
            
            // ترتيب: الأحدث أولاً أو الأعلى خطورة
            const sortedFingerprints = fingerprints.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

            sortedFingerprints.forEach(fp => {
                const tr = document.createElement("tr");
                
                // تحديد الألوان حسب الخطورة والحالة
                let riskClass = "risk-low";
                if (fp.risk_score >= 80) riskClass = "risk-high";
                else if (fp.risk_score >= 50) riskClass = "risk-medium";
                
                // تحديد حالة الزر (هل النظام قام بالحظر تلقائياً؟)
                const isBlocked = (fp.status === "BLOCKED");
                
                let actionButtonsHtml = '';

                // --- منطق التحكم اليدوي ---
                // زر الحظر (يظهر فقط إذا لم يكن محظوراً)
                if (!isBlocked) {
                    actionButtonsHtml += `
                        <button class="action-button block-now-button" 
                                onclick="manualAction('block', '${fp.fingerprint_id}', '${fp.user_id}')"
                                style="background-color: #dc3545; color: white;"
                                title="فرض الحظر يدوياً">
                            🚫 منع
                        </button>
                    `;
                }

                // زر السماح/رفع الحظر (يظهر دائماً لمنحك السيطرة)
                actionButtonsHtml += `
                    <button class="action-button unblock-user-button" 
                            onclick="manualAction('unblock', '${fp.fingerprint_id}', '${fp.user_id}')"
                            style="background-color: #28a745; color: white;"
                            title="إجبار النظام على السماح">
                        ✅ سماح / رفع حظر
                    </button>
                `;

                // زر الحذف
                actionButtonsHtml += `
                    <button class="action-button delete-button" 
                            onclick="manualAction('delete', '${fp.fingerprint_id}')"
                            style="background-color: #6c757d; color: white;">
                        🗑️ حذف
                    </button>
                `;
                
                // عرض الميزات السلوكية
                const featuresHtml = formatBehavioralFeatures(fp.behavioral_features);
                
                tr.innerHTML = `
                    <td><code>${fp.fingerprint_id.substring(0, 8)}...</code></td>
                    <td>${fp.user_id || 'Unknown'}</td>
                    <td><span class="risk-score ${riskClass}">${fp.risk_score}</span> <br> <small>${fp.status}</small></td>
                    <td class="behavioral-features">${featuresHtml}</td>
                    <td><div class="action-buttons" style="display:flex; gap:5px;">${actionButtonsHtml}</div></td>
                `;
                
                tbody.appendChild(tr);
            });
        }
        
        const now = new Date();
        const lastUp = document.getElementById("last-updated");
        if(lastUp) lastUp.textContent = `Last updated: ${now.toLocaleTimeString()}`;
            
    } catch (error) {
        console.error("Error loading fingerprints:", error);
        if (loadingMessage) loadingMessage.innerHTML = `<span style="color:red">Error connecting to API: ${error.message}</span>`;
    }
}

// دالة موحدة للتحكم اليدوي وإرسال الأوامر
async function manualAction(action, fingerprintId, userId) {
    let endpoint = "";
    let body = { fingerprint_id: fingerprintId };
    
    if (action === 'block') endpoint = '/api/v1/confirm-threat';
    if (action === 'unblock') {
        endpoint = '/api/v1/unblock-user';
        body = { user_id: userId }; // رفع الحظر يعتمد على User ID
    }
    if (action === 'delete') endpoint = '/api/v1/delete-fingerprint';

    if(!confirm(`هل أنت متأكد من تنفيذ: ${action}؟`)) return;

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (response.ok) {
            alert("✅ تم تنفيذ الأمر بنجاح");
            
            // إرسال إشارة لكل الصفحات المفتوحة لتحديث حالتها فوراً
            if (action === 'unblock') {
                localStorage.setItem('fingerprint_action', 'unblock');
                localStorage.setItem('fingerprint_user_id', userId);
                localStorage.setItem('fingerprint_updated', Date.now());
            }
            
            loadFingerprints(); // تحديث الجدول
        } else {
            alert("❌ فشل تنفيذ الأمر");
        }
    } catch (e) {
        alert("خطأ في الاتصال: " + e.message);
    }
}

function updateStats(fingerprints) {
    const totalCount = fingerprints.length;
    const highRiskCount = fingerprints.filter(fp => fp.risk_score >= 80).length;
    const mediumRiskCount = fingerprints.filter(fp => fp.risk_score >= 50 && fp.risk_score < 80).length;
    
    if(document.getElementById("total-count")) document.getElementById("total-count").textContent = totalCount;
    if(document.getElementById("high-risk-count")) document.getElementById("high-risk-count").textContent = highRiskCount;
    if(document.getElementById("medium-risk-count")) document.getElementById("medium-risk-count").textContent = mediumRiskCount;
}

function formatBehavioralFeatures(features) {
    if (!features || typeof features !== 'object') return 'No features';
    return Object.entries(features).map(([key, value]) => {
        let val = typeof value === 'number' ? value.toFixed(1) : value;
        return `<span class="feature-item" style="display:inline-block; background:#eee; padding:2px 5px; margin:2px; border-radius:4px; font-size:11px;">${key}: <b>${val}</b></span>`;
    }).join('');
}

// التشغيل التلقائي
if (typeof window !== "undefined") {
    window.addEventListener('DOMContentLoaded', () => {
        loadFingerprints();
        setInterval(loadFingerprints, 5000);
    });
}