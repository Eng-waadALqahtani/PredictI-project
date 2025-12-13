// ============================================================================
// CENTRALIZED EVENT TRACKING & RAPID CLICK DETECTION
// Used by all pages: Tawakkalna, Absher, Health Portal, etc.
// ============================================================================

// API Base URL: Use window.__PREDICTAI_API__ if set, otherwise use same-origin (empty string)
// This works for Render (same origin) and can be overridden for local development
const API_BASE = (typeof window !== "undefined" && window.__PREDICTAI_API__) || "";

// DEMO MODE: Set to true to suppress visible notifications during live demo
const DEMO_MODE = true;

// ============================================================================
// USER/DEVICE ID GENERATION
// ============================================================================

const DEMO_USER_ID = "user-8456123848";     // Fixed ID for demo (can be changed later)

// ============================================================================
// DEVICE ID GENERATION
// ============================================================================

/**
 * Generate or retrieve a unique device ID for this browser/device
 * The ID is stored in localStorage and persists across sessions
 */
function getOrGenerateDeviceId() {
    const STORAGE_KEY = 'predictai_device_id';
    
    // Try to get stored device ID from localStorage
    let deviceId = localStorage.getItem(STORAGE_KEY);
    
    // If not found, generate a new unique ID
    if (!deviceId) {
        // Generate a random unique identifier
        const uniquePart = Math.random().toString(36).substring(2, 15) + 
                          Math.random().toString(36).substring(2, 15);
        
        // Detect device type for prefix
        const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        const prefix = isMobile ? 'mobile' : 'desktop';
        
        deviceId = `${prefix}-${uniquePart}`;
        localStorage.setItem(STORAGE_KEY, deviceId);
        
        console.log(`📱 [DEVICE ID] Generated new device ID: ${deviceId}`);
    }
    
    return deviceId;
}

function getCurrentUserId() {
    return DEMO_USER_ID;
}

function getCurrentDeviceId() {
    return getOrGenerateDeviceId();
}

function getCurrentPlatform() {
    const href = window.location.pathname || "";
    if (href.includes("tawakkalna")) return "tawakkalna";
    if (href.includes("absher")) return "absher";
    if (href.includes("health-portal") || href.includes("health_portal")) return "health_portal";
    return "unknown";
}

// Debug: Log that events.js is loaded
console.log("✅ events.js loaded - Centralized event tracking active");
console.log(`   Demo User ID: ${DEMO_USER_ID}`);
console.log(`   Device ID: ${getCurrentDeviceId()}`);
console.log(`   API Base: ${API_BASE || '(same-origin)'}`);

// ============================================================================
// EVENT ID GENERATION
// ============================================================================

/**
 * Generate a unique event ID (UUID-like)
 */
function generateEventId() {
    return 'evt-' + Date.now().toString(36) + '-' + Math.random().toString(36).substring(2, 9);
}

// ============================================================================
// OFFLINE QUEUE MANAGEMENT
// ============================================================================

const EVENT_QUEUE_KEY = 'predictai_event_queue';

/**
 * Add event to offline queue
 */
function queueEvent(payload) {
    try {
        const queue = JSON.parse(localStorage.getItem(EVENT_QUEUE_KEY) || '[]');
        queue.push({
            ...payload,
            queued_at: new Date().toISOString()
        });
        // Limit queue size to prevent storage bloat
        if (queue.length > 100) {
            queue.shift(); // Remove oldest
        }
        localStorage.setItem(EVENT_QUEUE_KEY, JSON.stringify(queue));
        console.log(`💾 [OFFLINE QUEUE] Event queued (queue size: ${queue.length})`);
    } catch (e) {
        console.error(`❌ [OFFLINE QUEUE] Failed to queue event:`, e);
    }
}

/**
 * Flush queued events
 */
async function flushEventQueue() {
    try {
        const queueStr = localStorage.getItem(EVENT_QUEUE_KEY);
        if (!queueStr) return;
        
        const queue = JSON.parse(queueStr);
        if (queue.length === 0) return;
        
        console.log(`📤 [OFFLINE QUEUE] Flushing ${queue.length} queued event(s)`);
        
        const successful = [];
        for (let i = 0; i < queue.length; i++) {
            const queuedPayload = queue[i];
            try {
                const url = `${API_BASE}/api/v1/event`;
                const response = await fetch(url, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(queuedPayload),
                    keepalive: true
                });
                
                if (response.ok) {
                    successful.push(i);
                    console.log(`✅ [OFFLINE QUEUE] Successfully sent queued event: ${queuedPayload.event_id || queuedPayload.event_type}`);
                } else {
                    console.warn(`⚠️ [OFFLINE QUEUE] Failed to send queued event (status: ${response.status})`);
                }
            } catch (err) {
                console.warn(`⚠️ [OFFLINE QUEUE] Error sending queued event:`, err);
                // Keep failed events in queue for retry
            }
        }
        
        // Remove successfully sent events from queue
        if (successful.length > 0) {
            const newQueue = queue.filter((_, idx) => !successful.includes(idx));
            if (newQueue.length === 0) {
                localStorage.removeItem(EVENT_QUEUE_KEY);
                console.log(`✅ [OFFLINE QUEUE] Queue cleared`);
            } else {
                localStorage.setItem(EVENT_QUEUE_KEY, JSON.stringify(newQueue));
                console.log(`📊 [OFFLINE QUEUE] ${newQueue.length} event(s) remaining in queue`);
            }
        }
    } catch (e) {
        console.error(`❌ [OFFLINE QUEUE] Error flushing queue:`, e);
    }
}

// ============================================================================
// GENERIC SEND EVENT HELPER
// ============================================================================

/**
 * Send event to the server via POST /api/v1/event
 * @param {string} eventType - Type of event (e.g., 'login_attempt', 'download_file')
 * @param {string} serviceName - Optional service name (e.g., 'lab_report_1')
 * @param {object} extra - Additional data to include in the event
 */
function sendEvent(eventType, serviceName = null, extra = {}) {
    const eventId = generateEventId();
  const payload = {
        event_id: eventId,
    event_type: eventType,
        user_id: getCurrentUserId(),
        device_id: getCurrentDeviceId(),
        timestamp1: new Date().toISOString(),
        service_name: serviceName,
        platform: getCurrentPlatform(),
        ...extra
    };

    const url = `${API_BASE}/api/v1/event`;
    
    // Detailed debug log
    console.log(`📤 [EVENT REQUEST] Sending event:`, {
        url: url,
        event_id: eventId,
        event_type: eventType,
        service_name: serviceName,
        payload: payload
    });

    return fetch(url, {
    method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        keepalive: true  // Ensure request completes even if page unloads
    })
    .then(async response => {
        const status = response.status;
        const statusText = response.statusText;
        
        console.log(`📥 [EVENT RESPONSE] Status: ${status} ${statusText}, URL: ${url}`);
        
        if (!response.ok) {
            // For page_view events with 403, this is expected if user is blocked - don't show warning
            if (eventType === 'page_view' && status === 403) {
                console.log(`ℹ️ [EVENT] page_view blocked (user may be blocked) - this is expected behavior`);
            } else {
                console.warn(`⚠️ [EVENT WARNING] Response not OK: ${status} ${statusText} for event type: ${eventType}`);
            }
        }
        
        // Read Content-Type header and handle accordingly
        const contentType = response.headers.get("content-type") || "";
        let responseData;
        
        if (contentType.includes("application/json")) {
            try {
                responseData = await response.json();
                console.log(`📥 [EVENT RESPONSE] JSON body:`, responseData);
            } catch (e) {
                console.error(`❌ [EVENT ERROR] Failed to parse JSON response:`, e);
                const text = await response.text();
                responseData = { ok: false, status: status, text: text };
                console.log(`📥 [EVENT RESPONSE] Text body (fallback):`, text);
            }
        } else {
            const text = await response.text();
            console.log(`📥 [EVENT RESPONSE] Text body (non-JSON):`, text);
            try {
                responseData = JSON.parse(text);
            } catch (e) {
                responseData = { ok: false, status: status, text: text };
            }
        }
        
        return { response: responseData, status: status, statusText: statusText };
    })
    .then(({ response: data, status, statusText }) => {
        console.log(`✅ [EVENT SENT] Type: ${eventType}, ID: ${eventId}, Status: ${status}, Response:`, data);
        
        // Check if user is blocked (403 or status: "blocked")
        if (status === 403 || (data && data.status === "blocked")) {
            console.warn("🚫 [BLOCKED] User is blocked - showing block overlay");
            showBlockOverlay(data.message || "تم حجب دخولك مؤقتاً بسبب سلوك مشبوه تم رصده على منصة حكومية أخرى");
            return { ...data, blocked: true };
        }
        
        if (data.fingerprint_generated) {
            console.warn("⚠️ Threat Fingerprint Generated:", data.fingerprint_id);
            if (!DEMO_MODE) {
            showNotification("Threat detected! Check dashboard for details.", "warning");
            } else {
                console.log("[DEMO_NOTIFICATION_SUPPRESSED] Threat detected! Check dashboard for details.");
            }
        }
        
        return data;
    })
    .catch(err => {
        console.error(`❌ [EVENT ERROR] Failed to send event:`, {
            event_id: eventId,
            event_type: eventType,
            url: url,
            error: err,
            error_message: err.message,
            error_stack: err.stack
        });
        console.error(`   Payload was:`, payload);
        
        // Queue event for offline retry
        queueEvent(payload);
        
        if (!DEMO_MODE) {
        showNotification("Failed to send event to server", "error");
        } else {
            console.log("[DEMO_NOTIFICATION_SUPPRESSED] Failed to send event to server - queued for retry");
}
        
        // Return error object instead of throwing
        return { ok: false, error: err.message, queued: true };
    });
}

// ============================================================================
// RAPID CLICK DETECTOR
// ============================================================================

/**
 * Attach rapid click detector to an element
 * Detects suspicious rapid clicking patterns and sends ui_suspicious_pattern events
 * @param {HTMLElement} element - The element to monitor
 * @param {object} options - Configuration options
 */
function attachRapidClickDetector(element, options = {}) {
    if (!element) return;

    const maxClicksShort = options.maxClicksShort ?? 5;
    const windowShortMs = options.windowShortMs ?? 1000; // 1 second
    const maxClicksLong = options.maxClicksLong ?? 15;
    const windowLongMs = options.windowLongMs ?? 5000; // 5 seconds

    let clickTimes = [];
    let lastSuspiciousEvent = 0;
    const SUSPICIOUS_EVENT_COOLDOWN = 2000; // Don't spam events, wait 2 seconds between suspicious events

    element.addEventListener("click", () => {
        const now = Date.now();
        clickTimes.push(now);

        // Remove older than long window
        clickTimes = clickTimes.filter(t => now - t <= windowLongMs);

        const clicksShort = clickTimes.filter(t => now - t <= windowShortMs).length;
        const clicksLong = clickTimes.length;

        // Check if suspicious pattern detected and cooldown has passed
        if ((clicksShort >= maxClicksShort || clicksLong >= maxClicksLong) && 
            (now - lastSuspiciousEvent) >= SUSPICIOUS_EVENT_COOLDOWN) {
            
            // Suspicious rapid clicking pattern
            console.warn(`🚨 Rapid click detected: ${clicksShort} clicks in ${windowShortMs}ms, ${clicksLong} clicks in ${windowLongMs}ms`);
            
            sendEvent("ui_suspicious_pattern", null, {
                pattern: "rapid_clicks",
                clicks_short: clicksShort,
                window_short_ms: windowShortMs,
                clicks_long: clicksLong,
                window_long_ms: windowLongMs,
                element_id: element.id || element.className || "unknown",
                page: getCurrentPlatform()
            }).then(result => {
                if (result && result.fingerprint_generated) {
                    console.warn(`⚠️ [RAPID CLICKS] Threat fingerprint created! ID: ${result.fingerprint_id}, Risk: ${result.risk_score}`);
                }
            });
            
            lastSuspiciousEvent = now;
        }
    });
}

// ============================================================================
// MASS DOWNLOAD ATTACK SIMULATION
// ============================================================================

/**
 * Simulate a mass download attack (for demo purposes)
 * Sends many download_file events rapidly to trigger threat detection
 */
function simulateMassDownloadAttack() {
    console.log("🚨 Starting mass download attack simulation...");
    
    const services = [
        "lab_report_1",
        "lab_report_2",
        "xray_1",
        "full_history",
        "insurance_report",
        "vaccination_certificate",
        "medical_report_1",
        "medical_report_2"
    ];

    // Send many download events quickly
    for (let i = 0; i < 20; i++) {
        setTimeout(() => {
            const serviceName = services[i % services.length];
            sendEvent("download_file", serviceName, {
                file_size: Math.floor(Math.random() * 5000000) + 100000, // Random size between 100KB-5MB
                download_speed: Math.floor(Math.random() * 10000) + 1000 // Random speed
            });
        }, i * 100); // every 100ms
    }

    // Also mark explicit suspicious UI pattern event
    setTimeout(() => {
        sendEvent("ui_suspicious_pattern", null, {
            pattern: "mass_download",
            estimated_files: 20,
            time_window_ms: 2000
        });
    }, 2100);
}

// ============================================================================
// HIGH-SPEED ATTACK SIMULATION (Legacy - kept for compatibility)
// ============================================================================

/**
 * Trigger High-Speed Attack Simulation
 * Sends 20 high-risk events (update_mobile_attempt) in 2 seconds
 * Made available globally for keyboard shortcuts
 */
window.triggerHighSpeedAttack = function triggerHighSpeedAttack() {
    console.log("🚨 Starting high-speed attack simulation...");
    
    const totalEvents = 20;
    const durationMs = 2000; // 2 seconds
    const intervalMs = durationMs / totalEvents; // ~100ms between events
    
    let eventCount = 0;
    
    const attackInterval = setInterval(() => {
        // Send high-risk event type: update_mobile_attempt
        sendEvent("update_mobile_attempt");
        eventCount++;
        
        // Also send some other events for variety
        if (eventCount % 3 === 0) {
            sendEvent("view_digital_id");
        }
        
        if (eventCount >= totalEvents) {
            clearInterval(attackInterval);

            console.log(`✅ Attack simulation complete: ${eventCount} events sent in ${durationMs}ms`);
            if (!DEMO_MODE) {
            showNotification(
                `Attack simulation complete! ${eventCount} events sent. Check dashboard for threat fingerprints.`,
                "warning"
            );
            } else {
                console.log(`[DEMO_NOTIFICATION_SUPPRESSED] Attack simulation complete! ${eventCount} events sent. Check dashboard for threat fingerprints.`);
            }
}
    }, intervalMs);
    
    // Also send a burst at the end for extra intensity
    setTimeout(() => {
        for (let i = 0; i < 5; i++) {
            setTimeout(() => {
                sendEvent("update_mobile_attempt");
            }, i * 50);
        }
    }, durationMs - 250);
}

// ============================================================================
// BLOCK OVERLAY HELPER
// ============================================================================

/**
 * Show block overlay when user is blocked
 */
/**
 * Show block overlay when user is blocked
 */
function showBlockOverlay(message) {
    // 1. استثناء لوحة التحكم والصفحات الإدارية من الحجب
    const currentPath = window.location.pathname;
    // قائمة الصفحات التي لا يجب حجبها أبداً (صفحات الأدمن)
    const adminPages = ['dashboard.html', 'soc-admin', 'hub.html', 'database-view.html'];
    
    for (let page of adminPages) {
        if (currentPath.includes(page)) {
            console.log("⚠️ User is blocked, but overlay suppressed on Admin/Dashboard page.");
            return; // الخروج من الدالة وعدم إظهار الحجب
        }
    }

    // 2. كود الحجب الطبيعي لباقي الصفحات (أبشر وتوكلنا)
    let overlay = document.getElementById('block-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'block-overlay';
        overlay.style.cssText = `
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.9); /* خلفية أغمق */
            align-items: center;
            justify-content: center;
            z-index: 99999;
            backdrop-filter: blur(5px);
            display: flex;
            flex-direction: column;
        `;
        
        // تمييز رسالة الحظر حسب المنصة (جمالية فقط)
        const platform = getCurrentPlatform();
        const platformName = platform === 'absher' ? 'أبشر' : (platform === 'tawakkalna' ? 'توكلنا' : 'المنصة الوطنية');

        overlay.innerHTML = `
            <div style="background: white; padding: 40px; border-radius: 16px; max-width: 500px; text-align: center; border-top: 5px solid #c62828;">
                <div style="font-size: 50px; margin-bottom: 20px;">🚫</div>
                <h3 style="color: #c62828; font-size: 24px; margin-bottom: 15px; font-weight: 800;">
                    تم إيقاف حسابك في ${platformName}
                </h3>
                <p id="block-message" style="color: #444; font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
                    ${message || 'تم رصد نشاط يهدد أمن البيانات. تم تعليق الهوية الوطنية الرقمية الخاصة بك مؤقتاً في جميع الأنظمة الحكومية.'}
                </p>
                <div style="background-color: #fff3cd; color: #856404; padding: 10px; border-radius: 4px; font-size: 12px; margin-bottom: 20px;">
                    ملاحظة: هذا الحظر مركزي ويشمل جميع الخدمات المرتبطة بالهوية الوطنية.
                </div>
                <button onclick="location.reload()" 
                        style="padding: 10px 20px; background: #333; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    تحقق مجدداً
                </button>
            </div>
        `;
        document.body.appendChild(overlay);
    }
    
    overlay.style.display = 'flex';
}

/**
 * Hide block overlay
 */
function hideBlockOverlay() {
    const overlay = document.getElementById('block-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

// ============================================================================
// NOTIFICATION HELPER
// ============================================================================

/**
 * Show a notification to the user
 * In DEMO_MODE, notifications are suppressed and only logged to console
 */
function showNotification(message, type = "info") {
    if (DEMO_MODE) {
        console.log("[DEMO_NOTIFICATION_SUPPRESSED]", type, message);
        return;
    }
    
    // Create notification element
    const notification = document.createElement("div");
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === "warning" ? "#ff6b6b" : type === "error" ? "#e03131" : "#667eea"};
        color: white;
        padding: 15px 25px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        z-index: 10000;
        font-size: 14px;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = message;
    
    // Add animation
    const style = document.createElement("style");
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
    `;
    document.head.appendChild(style);
    
    document.body.appendChild(notification);
    
    // Remove after 4 seconds
    setTimeout(() => {
        notification.style.animation = "slideIn 0.3s ease-out reverse";
        setTimeout(() => {
            notification.remove();
            style.remove();
        }, 300);
    }, 4000);
}

// ============================================================================
// AUTO-ATTACH HANDLERS ON PAGE LOAD
// ============================================================================

if (typeof window !== "undefined") {
    // Set up keyboard shortcut handler immediately (before DOMContentLoaded)
    function setupKeyboardShortcut() {
        const handleKeyDown = (e) => {
            // Check for Ctrl + Shift + A (case-insensitive, works with Ctrl or Cmd)
            const isCtrlShiftA = (e.ctrlKey || e.metaKey) && 
                                 e.shiftKey && 
                                 (e.key === "A" || e.key === "a" || e.keyCode === 65 || e.which === 65);
            
            if (isCtrlShiftA) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                console.log("🔐 [SECRET TRIGGER] Keyboard shortcut detected: Ctrl+Shift+A");
                
                // Call the function (works with both window.triggerHighSpeedAttack and direct call)
                if (typeof window.triggerHighSpeedAttack === 'function') {
                    window.triggerHighSpeedAttack();
                } else if (typeof triggerHighSpeedAttack === 'function') {
                    triggerHighSpeedAttack();
                } else {
                    console.error("❌ triggerHighSpeedAttack function not found!");
                }
                return false;
            }
        };
        
        // Add listener to both window and document for maximum compatibility
        window.addEventListener("keydown", handleKeyDown, true);
        document.addEventListener("keydown", handleKeyDown, true);
        
        console.log("✅ Keyboard shortcut handler registered: Ctrl + Shift + A");
    }
    
    // Set up immediately if DOM is ready, otherwise wait
    if (document.readyState === "loading") {
        window.addEventListener("DOMContentLoaded", () => {
            setupKeyboardShortcut();
        });
    } else {
        setupKeyboardShortcut();
    }
    
    // Flush queued events and send page_view on DOMContentLoaded
    window.addEventListener("DOMContentLoaded", () => {
        // Flush offline queue immediately
        flushEventQueue();
        
        // Send guaranteed page_view event (silently handle 403 errors as they're expected for blocked users)
        sendEvent("page_view", null, {
            page_url: window.location.href,
            page_path: window.location.pathname,
            referrer: document.referrer || null
        }).catch(err => {
            // Silently handle errors for page_view - 403 is expected if user is blocked
            if (err.message && err.message.includes('403')) {
                console.log("[EVENT] page_view blocked (user may be blocked) - continuing silently");
            } else {
                console.warn("[EVENT] page_view event failed, but continuing:", err);
            }
        });
        
        // Set up periodic queue flush (every 10 seconds, stops when queue is empty)
        const flushInterval = setInterval(() => {
            flushEventQueue().then(() => {
                // Stop interval if queue is empty
                const queueStr = localStorage.getItem(EVENT_QUEUE_KEY);
                if (!queueStr || JSON.parse(queueStr).length === 0) {
                    clearInterval(flushInterval);
                    console.log("✅ [OFFLINE QUEUE] Periodic flush stopped - queue is empty");
                }
            });
        }, 10000);
    });
    
    // Main event tracking initialization
window.addEventListener("DOMContentLoaded", () => {
        const platform = getCurrentPlatform();
        console.log(`📍 Platform detected: ${platform}`);
        
        // ============================================
        // AUTO-ATTACH RAPID CLICK DETECTORS
        // ============================================
        
        // Common login buttons that exist on Tawakkalna and Absher pages
        const loginButton = document.querySelector("[data-track='login-submit']") || 
                           document.querySelector("button[type='submit']") ||
                           document.querySelector("#loginButton") ||
                           document.querySelector(".login-button");
        
        if (loginButton) {
            attachRapidClickDetector(loginButton);
            
            // Wrap existing onclick handlers
            const existingOnClick = loginButton.onclick;
            loginButton.addEventListener("click", (e) => {
                // Send tracking event
                sendEvent("login_click", null, {
                    page: getCurrentPlatform()
                });
                
                // Call existing onclick if present
                if (existingOnClick) {
                    existingOnClick.call(loginButton, e);
                }
            }, true); // Use capture phase to run before onclick
        }
        
        // Also attach to all buttons with class "service-btn" or "login-button"
        // This ensures rapid click detection works even with onclick handlers
        document.querySelectorAll(".service-btn, .login-button, button[type='submit'], #loginButton").forEach(btn => {
            // Only attach if not already attached
            if (!btn.hasAttribute('data-rapid-click-attached')) {
                attachRapidClickDetector(btn);
                btn.setAttribute('data-rapid-click-attached', 'true');
                console.log(`✅ [RAPID CLICK] Attached detector to button:`, btn.className || btn.id);
        }
        });
        
        // Sensitive actions like downloading files, opening services, etc.
        // Attach rapid click detector to buttons with data-track-service
        document.querySelectorAll("[data-track-service]").forEach(btn => {
            const serviceName = btn.getAttribute("data-track-service");
            attachRapidClickDetector(btn);
            
            // Wrap existing onclick handlers to ensure event tracking
            const existingOnClick = btn.onclick;
            btn.addEventListener("click", (e) => {
                // Send tracking event
                sendEvent("view_service", serviceName, {
                    page: getCurrentPlatform()
            });
                
                // Call existing onclick if present
                if (existingOnClick) {
                    existingOnClick.call(btn, e);
                }
            }, true); // Use capture phase to run before onclick
        });
        
        // Download buttons
        document.querySelectorAll("[data-track='download']").forEach(btn => {
            const fileName = btn.getAttribute("data-file-name") || "unknown";
            attachRapidClickDetector(btn);
            btn.addEventListener("click", () => {
                sendEvent("download_file", fileName);
            });
        });
        
        // Optional: any button that we mark with data-attack-trigger="true" will simulate a mass attack
        document.querySelectorAll("[data-attack-trigger='true']").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                simulateMassDownloadAttack();
            });
        });
        
        // ============================================
        // SECRET ATTACK TRIGGERS (Hidden from audience)
        // ============================================
        
        // OPTION B: Hidden click gesture (3 clicks on logo within 2 seconds)
        let logoClickTimestamps = [];
        const LOGO_CLICK_WINDOW = 2000; // 2 seconds
        const LOGO_CLICK_THRESHOLD = 3; // 3 clicks
        
        // Try to find logo elements (works for both Tawakkalna and Absher)
        const logoSelectors = [
            '.header-logo',
            '.logo-icon',
            '.tawakkalna-logo',
            '.vision-logo',
            '.vision-logo-img',
            '[class*="logo"]'
        ];
        
        logoSelectors.forEach(selector => {
            const logoElements = document.querySelectorAll(selector);
            logoElements.forEach(logoEl => {
                logoEl.addEventListener("click", (e) => {
                    const now = Date.now();
                    logoClickTimestamps.push(now);
                    
                    // Keep only clicks within the time window
                    logoClickTimestamps = logoClickTimestamps.filter(
                        ts => now - ts <= LOGO_CLICK_WINDOW
                    );
                    
                    // Check if threshold reached
                    if (logoClickTimestamps.length >= LOGO_CLICK_THRESHOLD) {
                        console.log("🔐 [SECRET TRIGGER] Logo click gesture detected (3 clicks in 2 seconds)");
                        logoClickTimestamps = []; // Reset
                        
                        // Call the function (works with both window.triggerHighSpeedAttack and direct call)
                        if (typeof window.triggerHighSpeedAttack === 'function') {
                            window.triggerHighSpeedAttack();
                        } else if (typeof triggerHighSpeedAttack === 'function') {
                            triggerHighSpeedAttack();
                        } else {
                            console.error("❌ triggerHighSpeedAttack function not found!");
                        }
                    }
                });
            });
        });
        
        console.log("✅ Event tracking initialized:");
        console.log("   - Platform:", platform);
        console.log("   - Rapid click detectors attached");
        console.log("   - Keyboard shortcut: Ctrl + Shift + A");
        console.log("   - Logo gesture: 3 clicks on logo within 2 seconds");
    });
}

// ============================================================================
// GLOBAL FUNCTIONS FOR CONSOLE TESTING
// ============================================================================

if (typeof window !== "undefined") {
    // Make functions available globally for console testing
    window.sendEvent = sendEvent;
    window.simulateMassDownloadAttack = simulateMassDownloadAttack;
    window.flushEventQueue = flushEventQueue;
    window.testAttack = function() {
        console.log("🧪 Testing attack trigger...");
        if (typeof window.triggerHighSpeedAttack === 'function') {
            window.triggerHighSpeedAttack();
        } else {
            console.error("❌ triggerHighSpeedAttack not available yet. Wait for page to load.");
        }
    };
    console.log("💡 Global functions available: sendEvent(), simulateMassDownloadAttack(), flushEventQueue(), testAttack()");
}
