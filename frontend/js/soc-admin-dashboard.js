// soc-admin-dashboard.js

// Flask backend port - automatically detect the current host
// Use same-origin if hostname is localhost/127.0.0.1, otherwise use current origin
const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') 
    ? `${window.location.protocol}//${window.location.hostname}:5000`
    : ''; // Same-origin for Render deployment

// Track previous fingerprint count for notifications
let previousFingerprintCount = 0;
let previousFingerprintIds = new Set();

/**
 * Load fingerprints from the API and display them in the SOC admin dashboard
 */
async function loadFingerprints() {
    const loadingMessage = document.getElementById("loading-message");
    const emptyState = document.getElementById("empty-state");
    const table = document.getElementById("fingerprints-table");
    const tbody = document.getElementById("fingerprints-tbody");
    
    if (previousFingerprintCount === 0 && loadingMessage) loadingMessage.style.display = "block";
    
    try {
        const response = await fetch(`${API_BASE}/api/v1/fingerprints`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            },
            cache: 'no-store'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);
        }
        
        const fingerprints = await response.json();
        
        // Validate response is an array
        if (!Array.isArray(fingerprints)) {
            console.warn('Expected array but got:', typeof fingerprints);
            throw new Error('Invalid response format: expected array');
        }
        
        if (loadingMessage) loadingMessage.style.display = "none";
        updateStats(fingerprints);
        if (tbody) tbody.innerHTML = "";
        
        if (fingerprints.length === 0) {
            if (emptyState) emptyState.style.display = "block";
            if (table) table.style.display = "none";
        } else {
            if (emptyState) emptyState.style.display = "none";
            if (table) table.style.display = "table";
            
            const sortedFingerprints = fingerprints.sort((a, b) => new Date(b.timestamp || 0) - new Date(a.timestamp || 0));
            
            sortedFingerprints.forEach(fp => {
                const tr = document.createElement("tr");
                
                // Styling Logic
                let riskClass = fp.risk_score >= 80 ? "risk-high" : (fp.risk_score >= 50 ? "risk-medium" : "risk-low");
                let statusText = "نشطة";
                let statusStyle = "background-color: #ffec99; color: #e67700;";
                
                if (fp.status === "BLOCKED") { statusText = "محظورة"; statusStyle = "background-color: #ffa8a8; color: #c92a2a;"; }
                else if (fp.status === "CLEARED") { statusText = "مُزال المنع"; statusStyle = "background-color: #b2f2bb; color: #2b8a3e;"; }
                else if (fp.status === "PENDING") { statusText = "قيد المراجعة"; statusStyle = "background-color: #e7f5ff; color: #1c7ed6;"; }

                // REASONS LOGIC: Extract and display reasons at the top of features
                let reasonsHtml = '';
                if (fp.behavioral_features && fp.behavioral_features.detection_reasons) {
                    const reasons = fp.behavioral_features.detection_reasons;
                    if (Array.isArray(reasons) && reasons.length > 0) {
                        reasonsHtml = `<div class="reasons-container">
                            ${reasons.map(r => `<div class="reason-badge">⚠️ ${formatReasonText(r)}</div>`).join('')}
                        </div>`;
                    }
                }

                // Vertical Buttons Logic
                const isBlocked = (fp.status === "BLOCKED");
                let actionButtonsHtml = '';
                
                if (isBlocked) {
                    actionButtonsHtml += `<button class="soc-action-btn btn-green" data-action="unblock-user" data-user-id="${fp.user_id}" data-fingerprint-id="${fp.fingerprint_id}"><i>🔓</i> إزالة المنع</button>`;
                } else {
                    actionButtonsHtml += `<button class="soc-action-btn btn-red" data-action="block-now" data-fingerprint-id="${fp.fingerprint_id}"><i>✋</i> تأكيد التهديد</button>`;
                }
                actionButtonsHtml += `<button class="soc-action-btn btn-grey" data-action="delete" data-fingerprint-id="${fp.fingerprint_id}"><i>🗑️</i> حذف</button>`;

                const featuresHtml = formatBehavioralFeatures(fp.behavioral_features);
                
                tr.innerHTML = `
                    <td style="text-align:center;">
                        <span class="fingerprint-id-badge">${fp.fingerprint_id.substring(0, 10)}...</span>
                        <div style="font-size:11px; color:#999; margin-top:5px;">${new Date(fp.timestamp || Date.now()).toLocaleTimeString('ar-SA')}</div>
                    </td>
                    <td style="text-align:center;">
                        <div class="user-info">${fp.user_id || 'Unknown'}</div>
                        <small style="color:#666;">${fp.platform || 'System'}</small>
                    </td>
                    <td style="text-align:center;">
                        <div class="risk-box ${riskClass}">${fp.risk_score}</div>
                    </td>
                    <td style="text-align:center;">
                        <span style="padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 13px; ${statusStyle}">${statusText}</span>
                    </td>
                    <td class="behavioral-features">
                        ${reasonsHtml}
                        ${featuresHtml}
                    </td>
                    <td>
                        <div class="action-buttons-vertical">${actionButtonsHtml}</div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
        if(document.getElementById("last-updated")) document.getElementById("last-updated").textContent = `آخر تحديث: ${new Date().toLocaleTimeString('ar-SA')}`;
        
        // Update previous count for notifications
        previousFingerprintCount = fingerprints.length;
        previousFingerprintIds = new Set(fingerprints.map(fp => fp.fingerprint_id));
        
    } catch (error) {
        console.error("Error loading fingerprints:", error);
        if (loadingMessage) loadingMessage.style.display = "none";
        if (emptyState) {
            emptyState.style.display = "block";
            emptyState.innerHTML = `
                <h3>⚠️ خطأ في تحميل البصمات</h3>
                <p>${error.message || 'حدث خطأ غير متوقع'}</p>
                <button onclick="loadFingerprints()" style="margin-top: 10px; padding: 8px 16px; background: #1e40af; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    🔄 إعادة المحاولة
                </button>
            `;
        }
        if (table) table.style.display = "none";
    }
}

/**
 * Update statistics cards
 */
function updateStats(fingerprints) {
    const totalCount = fingerprints.length;
    const activeCount = fingerprints.filter(fp => fp.status === "ACTIVE" || fp.status === "PENDING").length;
    const blockedCount = fingerprints.filter(fp => fp.status === "BLOCKED").length;
    const clearedCount = fingerprints.filter(fp => fp.status === "CLEARED").length;
    
    const totalEl = document.getElementById("total-count");
    const activeEl = document.getElementById("active-count");
    const blockedEl = document.getElementById("blocked-count");
    const clearedEl = document.getElementById("cleared-count");
    
    if (totalEl) totalEl.textContent = totalCount;
    if (activeEl) activeEl.textContent = activeCount;
    if (blockedEl) blockedEl.textContent = blockedCount;
    if (clearedEl) clearedEl.textContent = clearedCount;
}

/**
 * Map raw reason codes to human-readable text
 */
function formatReasonText(reason) {
    const map = {
        'rapid_clicks': 'نقرات سريعة (Suspicious UI Pattern)',
        'mass_download': 'تحميل جماعي للملفات',
        'browser_hopping': 'تغيير متصفح متكرر (Browser Hopping)',
        'multi_account_attack': 'هجوم متعدد الحسابات',
        'geographic_jump': 'قفزة جغرافية مستحيلة',
        'device_change': 'تغيير الجهاز'
    };
    return map[reason] || reason.replace(/_/g, ' ');
}

/**
 * Updated formatter that EXCLUDES detection_reasons from the generic list (since we show them at the top)
 */
function formatBehavioralFeatures(features) {
    if (!features || typeof features !== 'object') return '<span style="color:#999;">لا توجد بيانات</span>';
    
    // Explicitly ignore 'detection_reasons' here because we render them separately
    const ignoredKeys = ['detection_reasons', 'risk_boost_device_context', 'risk_boost_attack_profile', 'similarity_detected', 'reason'];
    
    return Object.entries(features)
        .filter(([key]) => !ignoredKeys.includes(key))
        .map(([key, value]) => {
            const label = key.replace(/_/g, ' ').replace(/(?:^|\s)\S/g, a => a.toUpperCase());
            let valDisplay = value;
            if (typeof value === 'number') valDisplay = value % 1 !== 0 ? value.toFixed(2) : value;
            if (typeof value === 'boolean') valDisplay = value ? 'True' : 'False';
            return `<span class="feature-tag">${label}: <b>${valDisplay}</b></span>`;
        }).join('');
}

/**
 * Block a fingerprint (confirm threat)
 */
async function blockFingerprint(fingerprintId) {
    if (!confirm(`هل أنت متأكد من منع المستخدم للبصمة ${fingerprintId}؟`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/v1/confirm-threat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fingerprint_id: fingerprintId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        console.log('✅ [BLOCK] Success:', data);
        alert('✅ تم منع المستخدم بنجاح');
        
        // Refresh dashboard
        refreshDashboard();
        
    } catch (error) {
        console.error("Error blocking fingerprint:", error);
        alert(`خطأ في منع المستخدم: ${error.message}`);
        throw error;
    }
}

/**
 * Clear fingerprint (set status to CLEARED)
 */
async function clearFingerprint(fingerprintId) {
    if (!confirm(`هل تريد إزالة التنبيه للبصمة ${fingerprintId}؟`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/v1/clear-fingerprint`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fingerprint_id: fingerprintId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        console.log('✅ [CLEAR] Success:', data);
        alert(`✅ ${data.message || 'تم إزالة التنبيه بنجاح'}`);
        
        // Refresh dashboard
        refreshDashboard();
        
    } catch (error) {
        console.error("Error clearing fingerprint:", error);
        alert(`خطأ في إزالة التنبيه: ${error.message}`);
        throw error;
    }
}

/**
 * Unblock a user by clearing their fingerprints
 */
async function unblockUser(userId, fingerprintId) {
    // Customize message based on context
    const msg = `هل أنت متأكد من السماح للمستخدم ${userId} وإزالة أي قيود؟`;
    
    if (!confirm(msg)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/v1/unblock-user`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        console.log('✅ [UNBLOCK] Success:', data);
        alert(`✅ ${data.message || 'تم رفع الحظر بنجاح'}`);
        
        // Trigger cross-tab synchronization for immediate unblock
        const now = Date.now().toString();
        localStorage.setItem('fingerprint_updated', now);
        localStorage.setItem('fingerprint_action', 'unblock');
        localStorage.setItem('fingerprint_user_id', userId);
        
        // Dispatch storage event for cross-tab communication
        window.dispatchEvent(new StorageEvent('storage', {
            key: 'fingerprint_updated',
            newValue: now
        }));
        
        // Refresh dashboard
        refreshDashboard();
        
    } catch (error) {
        console.error("Error unblocking user:", error);
        alert(`خطأ في العملية: ${error.message}`);
    }
}

/**
 * Refresh dashboard - reloads fingerprints and updates stats
 */
function refreshDashboard() {
    loadFingerprints();
}

/**
 * Delete a fingerprint
 */
async function deleteFingerprint(fingerprintId) {
    if (!confirm(`هل أنت متأكد من حذف البصمة ${fingerprintId} نهائياً؟`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/v1/delete-fingerprint`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fingerprint_id: fingerprintId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        console.log('✅ [DELETE] Success:', data);
        alert(`✅ ${data.message || 'تم حذف البصمة بنجاح'}`);
        
        // Refresh dashboard
        refreshDashboard();
        
    } catch (error) {
        console.error("Error deleting fingerprint:", error);
        alert(`خطأ في حذف البصمة: ${error.message}`);
        throw error;
    }
}

/**
 * Show success message
 */
function showSuccessMessage(message) {
    const successMsg = document.getElementById("successMessage");
    if (!successMsg) return;
    
    successMsg.textContent = message;
    successMsg.style.display = "block";
    
    setTimeout(() => {
        successMsg.style.animation = "slideIn 0.3s ease-out reverse";
        setTimeout(() => {
            successMsg.style.display = "none";
            successMsg.style.animation = "slideIn 0.3s ease-out";
        }, 300);
    }, 3000);
}

/**
 * Show notification for new fingerprints
 */
function showNewFingerprintNotification(newFingerprints) {
    // Only show if we have actual new fingerprints that are risky enough or pending
    const notableFingerprints = newFingerprints.filter(fp => fp.risk_score >= 50 || fp.status === 'PENDING');
    
    if (notableFingerprints.length === 0) return;

    const notification = document.createElement("div");
    notification.className = "new-fingerprint-notification";
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: linear-gradient(135deg, #c92a2a 0%, #e03131 100%);
        color: white;
        padding: 20px 30px;
        border-radius: 10px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        animation: slideDown 0.5s ease-out;
        max-width: 500px;
        text-align: center;
    `;
    
    const highRiskCount = notableFingerprints.filter(fp => fp.risk_score >= 80).length;
    
    notification.innerHTML = `
        <div style="font-size: 24px; margin-bottom: 10px;">🚨</div>
        <div style="font-weight: bold; font-size: 18px; margin-bottom: 5px;">
            تم رصد ${notableFingerprints.length} نشاط مشبوه جديد!
        </div>
        <div style="font-size: 14px; opacity: 0.9;">
            ${highRiskCount > 0 ? `${highRiskCount} عالية الخطورة - تتطلب مراجعة فورية` : 'يرجى مراجعة القائمة'}
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Remove notification after 5 seconds
    setTimeout(() => {
        notification.style.animation = "slideUp 0.5s ease-out";
        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 500);
    }, 5000);
}

// Add CSS animations
const style = document.createElement("style");
style.textContent = `
    @keyframes slideDown {
        from { transform: translateX(-50%) translateY(-100px); opacity: 0; }
        to { transform: translateX(-50%) translateY(0); opacity: 1; }
    }
    @keyframes slideUp {
        from { transform: translateX(-50%) translateY(0); opacity: 1; }
        to { transform: translateX(-50%) translateY(-100px); opacity: 0; }
    }
    .status-pending {
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #ffeeba;
    }
    .status-active {
        background-color: #d4edda;
        color: #155724;
    }
    .status-blocked {
        background-color: #f8d7da;
        color: #721c24;
    }
    .status-cleared {
        background-color: #e2e3e5;
        color: #383d41;
    }
`;
document.head.appendChild(style);

// ADDED: Block/Unblock Actions - Event delegation for action buttons
if (typeof window !== "undefined") {
    window.addEventListener('DOMContentLoaded', () => {
        const tableContainer = document.getElementById('fingerprints-table') || document.querySelector('.fingerprints-container');
        if (tableContainer) {
            // Use event delegation to handle clicks on dynamically rendered buttons
            tableContainer.addEventListener('click', async (e) => {
                const button = e.target.closest('.action-button');
                if (!button) return;
                
                const action = button.getAttribute('data-action');
                const fingerprintId = button.getAttribute('data-fingerprint-id');
                const userId = button.getAttribute('data-user-id');
                
                // Disable button during request
                const originalText = button.textContent;
                button.disabled = true;
                button.style.opacity = '0.6';
                button.textContent = 'جاري المعالجة...';
                
                try {
                    if (action === 'block-now') {
                        await blockFingerprint(fingerprintId);
                    } else if (action === 'clear') {
                        await clearFingerprint(fingerprintId);
                    } else if (action === 'unblock-user') {
                        await unblockUser(userId, fingerprintId);
                    } else if (action === 'delete') {
                        await deleteFingerprint(fingerprintId);
                    }
                } catch (error) {
                    console.error(`Error in ${action} action:`, error);
                } finally {
                    // Re-enable button
                    button.disabled = false;
                    button.style.opacity = '1';
                    button.textContent = originalText;
                }
            });
        }
        
        loadFingerprints();
        
        // Auto-refresh every 5 seconds for real-time monitoring
        setInterval(loadFingerprints, 5000);
    });
}