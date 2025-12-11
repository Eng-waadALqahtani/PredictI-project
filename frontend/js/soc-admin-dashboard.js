// Flask backend port - automatically detect the current host
const API_BASE = `${window.location.protocol}//${window.location.hostname}:5000`;

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
    
    // Show loading state only on first load
    if (previousFingerprintCount === 0) {
        loadingMessage.style.display = "block";
    }
    emptyState.style.display = "none";
    table.style.display = "none";
    
    try {
        const response = await fetch(`${API_BASE}/api/v1/fingerprints`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const fingerprints = await response.json();
        
        // Hide loading
        loadingMessage.style.display = "none";
        
        // Check for new fingerprints
        const currentFingerprintIds = new Set(fingerprints.map(fp => fp.fingerprint_id));
        const newFingerprints = fingerprints.filter(fp => !previousFingerprintIds.has(fp.fingerprint_id));
        
        if (newFingerprints.length > 0 && previousFingerprintIds.size > 0) {
            // Show notification for new fingerprints
            showNewFingerprintNotification(newFingerprints);
        }
        
        // Update previous tracking
        previousFingerprintCount = fingerprints.length;
        previousFingerprintIds = currentFingerprintIds;
        
        // Update stats
        updateStats(fingerprints);
        
        // Clear existing rows
        tbody.innerHTML = "";
        
        if (fingerprints.length === 0) {
            emptyState.style.display = "block";
            table.style.display = "none";
        } else {
            emptyState.style.display = "none";
            table.style.display = "table";
            
            // Display fingerprints in the table (new ones first)
            const sortedFingerprints = fingerprints.sort((a, b) => {
                // Sort by status and risk score
                if (a.status === "ACTIVE" && b.status !== "ACTIVE") return -1;
                if (a.status !== "ACTIVE" && b.status === "ACTIVE") return 1;
                return b.risk_score - a.risk_score;
            });
            
            sortedFingerprints.forEach(fp => {
                const tr = document.createElement("tr");
                
                // Determine risk level styling
                let riskClass = "risk-low";
                if (fp.risk_score >= 80) {
                    riskClass = "risk-high";
                } else if (fp.risk_score >= 50) {
                    riskClass = "risk-medium";
                }
                
                // Determine status badge styling
                let statusClass = "status-active";
                let statusText = "نشطة";
                if (fp.status === "BLOCKED") {
                    statusClass = "status-blocked";
                    statusText = "محظورة";
                } else if (fp.status === "CLEARED") {
                    statusClass = "status-cleared";
                    statusText = "مُزال المنع";
                }
                
                // Format behavioral features
                const featuresHtml = formatBehavioralFeatures(fp.behavioral_features);
                
                // Format similar fingerprints badge if present
                let similarityBadge = '';
                if (fp.related_fingerprints && fp.related_fingerprints.length > 0) {
                    const blockedCount = fp.related_fingerprints.filter(rf => 
                        rf.status === 'BLOCKED' || rf.status === 'ACTIVE'
                    ).length;
                    const highestSim = Math.max(...fp.related_fingerprints.map(rf => rf.similarity || 0));
                    const simPercent = (highestSim * 100).toFixed(0);
                    
                    similarityBadge = `<span class="similarity-badge" title="Similar to ${fp.related_fingerprints.length} previous fingerprint(s), highest similarity: ${simPercent}%">
                        🔗 Similar to ${fp.related_fingerprints.length} previous${blockedCount > 0 ? ` (${blockedCount} BLOCKED/ACTIVE)` : ''}
                    </span>`;
                }
                
                // Determine if user is blocked (has ACTIVE fingerprint with risk >= 80)
                const isBlocked = fp.status === "ACTIVE" && fp.risk_score >= 80;
                
                tr.innerHTML = `
                    <td><code>${fp.fingerprint_id}</code>${similarityBadge}</td>
                    <td>${fp.user_id || 'غير محدد'}</td>
                    <td>
                        <span class="risk-score ${riskClass}">
                            ${fp.risk_score}
                        </span>
                    </td>
                    <td>
                        <span class="status-badge ${statusClass}">
                            ${statusText}
                        </span>
                    </td>
                    <td class="behavioral-features">
                        ${featuresHtml}
                    </td>
                    <td>
                        <div class="action-buttons">
                            ${fp.status === "ACTIVE" ? `
                                <button class="action-button unblock-button" 
                                        onclick="unblockUser('${fp.user_id}', '${fp.fingerprint_id}')"
                                        title="إزالة المنع عن المستخدم">
                                    🔓 إزالة المنع
                                </button>
                            ` : ''}
                            ${fp.status === "ACTIVE" ? `
                                <button class="action-button confirm-button" 
                                        onclick="confirmThreat('${fp.fingerprint_id}')"
                                        title="تأكيد التهديد">
                                    ✅ تأكيد التهديد
                                </button>
                            ` : ''}
                        </div>
                    </td>
                `;
                
                tbody.appendChild(tr);
            });
        }
        
        // Update last updated time
        const now = new Date();
        document.getElementById("last-updated").textContent = 
            `آخر تحديث: ${now.toLocaleTimeString('ar-SA')}`;
            
    } catch (error) {
        console.error("Error loading fingerprints:", error);
        loadingMessage.style.display = "none";
        emptyState.style.display = "block";
        emptyState.innerHTML = `
            <h3>خطأ في تحميل البصمات</h3>
            <p>${error.message}</p>
        `;
        table.style.display = "none";
    }
}

/**
 * Update the statistics cards
 */
function updateStats(fingerprints) {
    const totalCount = fingerprints.length;
    const activeCount = fingerprints.filter(fp => fp.status === "ACTIVE").length;
    const blockedCount = fingerprints.filter(fp => fp.status === "BLOCKED").length;
    const clearedCount = fingerprints.filter(fp => fp.status === "CLEARED").length;
    
    document.getElementById("total-count").textContent = totalCount;
    document.getElementById("active-count").textContent = activeCount;
    document.getElementById("blocked-count").textContent = blockedCount;
    document.getElementById("cleared-count").textContent = clearedCount;
}

/**
 * Format behavioral features for display
 */
function formatBehavioralFeatures(features) {
    if (!features || typeof features !== 'object') {
        return '<span class="feature-item">لا توجد خصائص</span>';
    }
    
    const featureItems = Object.entries(features).map(([key, value]) => {
        // Format key to be more readable
        const formattedKey = key
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase());
        
        // Format value appropriately
        let formattedValue = value;
        if (typeof value === 'number') {
            if (key.includes('per_minute') || key.includes('rate')) {
                formattedValue = value.toFixed(2);
            } else {
                formattedValue = value.toString();
            }
        }
        
        return `<span class="feature-item" title="${key}">${formattedKey}: <strong>${formattedValue}</strong></span>`;
    });
    
    return featureItems.join('');
}

/**
 * Unblock a user by clearing their fingerprints
 */
async function unblockUser(userId, fingerprintId) {
    if (!confirm(`هل أنت متأكد من إزالة المنع عن المستخدم ${userId}؟`)) {
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
        
        showSuccessMessage(`✅ ${data.message} (تم مسح ${data.cleared_fingerprints} بصمة)`);
        
        // Reload fingerprints
        setTimeout(() => {
            loadFingerprints();
        }, 1000);
        
    } catch (error) {
        console.error("Error unblocking user:", error);
        alert(`خطأ في إزالة المنع: ${error.message}`);
    }
}

/**
 * Confirm a threat fingerprint
 */
async function confirmThreat(fingerprintId) {
    if (!confirm(`هل تريد تأكيد التهديد للبصمة ${fingerprintId}؟`)) {
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
        
        showSuccessMessage(`✅ ${data.message}`);
        
        // Reload fingerprints
        setTimeout(() => {
            loadFingerprints();
        }, 1000);
        
    } catch (error) {
        console.error("Error confirming threat:", error);
        alert(`خطأ في تأكيد التهديد: ${error.message}`);
    }
}

/**
 * Show success message
 */
function showSuccessMessage(message) {
    const successMsg = document.getElementById("successMessage");
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
    
    const highRiskCount = newFingerprints.filter(fp => fp.risk_score >= 80).length;
    
    notification.innerHTML = `
        <div style="font-size: 24px; margin-bottom: 10px;">🚨</div>
        <div style="font-weight: bold; font-size: 18px; margin-bottom: 5px;">
            تم اكتشاف ${newFingerprints.length} بصمة تهديد جديدة!
        </div>
        <div style="font-size: 14px; opacity: 0.9;">
            ${highRiskCount > 0 ? `${highRiskCount} بصمة عالية الخطورة (≥80)` : 'جميع البصمات منخفضة الخطورة'}
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Remove notification after 5 seconds
    setTimeout(() => {
        notification.style.animation = "slideUp 0.5s ease-out";
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 500);
    }, 5000);
}

// Add CSS animations
const style = document.createElement("style");
style.textContent = `
    @keyframes slideDown {
        from {
            transform: translateX(-50%) translateY(-100px);
            opacity: 0;
        }
        to {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }
    }
    
    @keyframes slideUp {
        from {
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }
        to {
            transform: translateX(-50%) translateY(-100px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Load fingerprints on page load
if (typeof window !== "undefined") {
    window.addEventListener("DOMContentLoaded", () => {
        loadFingerprints();
        
        // Auto-refresh every 5 seconds for real-time monitoring
        setInterval(loadFingerprints, 5000);
    });
}

