// Flask backend port - automatically detect the current host
const API_BASE = `${window.location.protocol}//${window.location.hostname}:5000`;

/**
 * Load fingerprints from the API and display them in the dashboard
 */
async function loadFingerprints() {
    const loadingMessage = document.getElementById("loading-message");
    const emptyState = document.getElementById("empty-state");
    const table = document.getElementById("fingerprints-table");
    const tbody = document.getElementById("fingerprints-tbody");
    
    // Show loading state
    loadingMessage.style.display = "block";
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
            
            // Display fingerprints in the table
            fingerprints.forEach(fp => {
                const tr = document.createElement("tr");
                
                // Determine risk level styling
                let riskClass = "risk-low";
                if (fp.risk_score >= 80) {
                    riskClass = "risk-high";
                } else if (fp.risk_score >= 50) {
                    riskClass = "risk-medium";
                }
                
                // Format behavioral features
                const featuresHtml = formatBehavioralFeatures(fp.behavioral_features);
                
                tr.innerHTML = `
                    <td><code>${fp.fingerprint_id}</code></td>
                    <td>
                        <span class="risk-score ${riskClass}">
                            ${fp.risk_score}
                        </span>
                    </td>
                    <td class="behavioral-features">
                        ${featuresHtml}
                    </td>
                `;
                
                tbody.appendChild(tr);
            });
        }
        
        // Update last updated time
        const now = new Date();
        document.getElementById("last-updated").textContent = 
            `Last updated: ${now.toLocaleTimeString()}`;
            
    } catch (error) {
        console.error("Error loading fingerprints:", error);
        loadingMessage.style.display = "none";
        emptyState.style.display = "block";
        emptyState.innerHTML = `
            <h3>Error Loading Fingerprints</h3>
            <p>${error.message}</p>
            <p style="margin-top: 10px; color: #999;">Make sure the backend server is running on port 5000.</p>
        `;
        table.style.display = "none";
    }
}

/**
 * Update the statistics cards
 */
function updateStats(fingerprints) {
    const totalCount = fingerprints.length;
    const highRiskCount = fingerprints.filter(fp => fp.risk_score >= 80).length;
    const mediumRiskCount = fingerprints.filter(fp => fp.risk_score >= 50 && fp.risk_score < 80).length;
    
    document.getElementById("total-count").textContent = totalCount;
    document.getElementById("high-risk-count").textContent = highRiskCount;
    document.getElementById("medium-risk-count").textContent = mediumRiskCount;
}

/**
 * Format behavioral features for display
 */
function formatBehavioralFeatures(features) {
    if (!features || typeof features !== 'object') {
        return '<span class="feature-item">No features</span>';
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

// Load fingerprints on page load
if (typeof window !== "undefined") {
    window.addEventListener("DOMContentLoaded", () => {
        loadFingerprints();
        
        // Auto-refresh every 5 seconds
        setInterval(loadFingerprints, 5000);
    });
}
