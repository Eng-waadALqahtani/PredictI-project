from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class Event:
    """Event class representing a user action in the system"""
    event_type: str
    user_id: str
    device_id: str
    timestamp1: datetime
    platform: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_type: Optional[str] = None  # e.g., "mobile", "laptop", "tablet", "desktop"
    location: Optional[str] = None  # City name, e.g., "Riyadh", "Abha"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Event to dictionary for JSON serialization"""
        return {
            "event_type": self.event_type,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "timestamp1": self.timestamp1.isoformat(),
            "platform": self.platform,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "device_type": self.device_type,
            "location": self.location
        }


@dataclass
class ThreatFingerprint:
    """ThreatFingerprint class representing a detected behavioral anomaly"""
    fingerprint_id: str
    risk_score: int  # 0-100
    user_id: str = ""  # User ID associated with this fingerprint
    status: str = "ACTIVE"  # Status: 'ACTIVE', 'BLOCKED', 'CLEARED'
    behavioral_features: Dict[str, Any] = field(default_factory=dict)
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ThreatFingerprint to dictionary for JSON serialization"""
        result = {
            "fingerprint_id": self.fingerprint_id,
            "risk_score": self.risk_score,
            "user_id": self.user_id,
            "status": self.status,
            "behavioral_features": self.behavioral_features,
            "device_id": self.device_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent
        }
        
        # Add related_fingerprints if present (for similarity detection)
        if hasattr(self, 'related_fingerprints') and self.related_fingerprints:
            result["related_fingerprints"] = self.related_fingerprints
        
        return result
