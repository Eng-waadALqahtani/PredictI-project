// ============================================================================
// CENTRALIZED EVENT TRACKING & RAPID CLICK DETECTION
// Used by all pages: Tawakkalna, Absher, Health Portal, etc.
// ============================================================================

// Flask backend port - automatically detect the current host
// Dynamic API base URL: Use Render URL in production, localhost in development
// Make it available globally to avoid redeclaration errors
if (typeof window !== "undefined") {
    if (typeof window.API_BASE === "undefined") {
        // Check if running on Render or production environment
        const isRender = window.location.hostname.includes("render") || 
                        window.location.hostname.includes("onrender.com") ||
                        window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1";
        
        if (isRender) {
            window.API_BASE = "https://predictiq-backend.onrender.com";
        } else {
            window.API_BASE = `${window.location.protocol}//${window.location.hostname}:5000`;
        }
    }
}
const API_BASE = window.API_BASE || (window.location.hostname.includes("render") || window.location.hostname.includes("onrender.com")
    ? "https://predictiq-backend.onrender.com"
    : `${window.location.protocol}//${window.location.hostname}:5000`);

// DEMO MODE: Set to true to suppress visible notifications during live demo
const DEMO_MODE = true;

// ============================================================================
// DEMO USER/DEVICE IDs (Fixed for demo consistency)
// ============================================================================

const DEMO_USER_ID = "user-8456123848";     // Fixed ID for demo
const DEMO_DEVICE_ID = "device-demo-01";    // Fixed ID for demo

function getCurrentUserId() {
    return DEMO_USER_ID;
}

function getCurrentDeviceId() {
    return DEMO_DEVICE_ID;
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
console.log(`   Demo Device ID: ${DEMO_DEVICE_ID}`);

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
  const payload = {
    event_type: eventType,
        user_id: getCurrentUserId(),
        device_id: getCurrentDeviceId(),
        timestamp1: new Date().toISOString(),
        service_name: serviceName,
        platform: getCurrentPlatform(),
        ...extra
    };

    return fetch(`${API_BASE}/api/v1/event`, {
    method: "POST",
        headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        console.log(`📤 [EVENT SENT] Type: ${eventType}, Service: ${serviceName || 'N/A'}, Response:`, data);
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
        console.error("❌ Error sending event:", err);
        if (!DEMO_MODE) {
        showNotification("Failed to send event to server", "error");
        } else {
            console.log("[DEMO_NOTIFICATION_SUPPRESSED] Failed to send event to server");
}
        throw err;
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
                element_id: element.id || element.className || "unknown"
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
            loginButton.addEventListener("click", () => {
                // Normal login click event
                sendEvent("login_click");
            });
        }
        
        // Sensitive actions like downloading files, opening services, etc.
        document.querySelectorAll("[data-track-service]").forEach(btn => {
            const serviceName = btn.getAttribute("data-track-service");
            attachRapidClickDetector(btn);
            btn.addEventListener("click", () => {
                sendEvent("view_service", serviceName);
            });
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
    window.testAttack = function() {
        console.log("🧪 Testing attack trigger...");
        if (typeof window.triggerHighSpeedAttack === 'function') {
            window.triggerHighSpeedAttack();
        } else {
            console.error("❌ triggerHighSpeedAttack not available yet. Wait for page to load.");
        }
    };
    console.log("💡 Global functions available: sendEvent(), simulateMassDownloadAttack(), testAttack()");
}
