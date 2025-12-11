"""
Database setup and models using SQLAlchemy.

Supports SQLite by default (for local/demo) and PostgreSQL via DATABASE_URL environment variable.
Creates tables automatically on startup if they don't exist.
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional
import json

# Base class for declarative models
Base = declarative_base()


class FingerprintDB(Base):
    """
    Database model for threat fingerprints.
    Stores all fingerprint data with behavioral features as JSON.
    """
    __tablename__ = 'fingerprints'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Unique fingerprint identifier (same as ThreatFingerprint.fingerprint_id)
    fingerprint_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # User and device identifiers
    user_id = Column(String(255), nullable=False, index=True)
    device_id = Column(String(255), nullable=True)
    ip_address = Column(String(255), nullable=True, index=True)
    user_agent = Column(String(512), nullable=True)
    
    # Risk assessment
    risk_score = Column(Integer, nullable=False, default=0)
    status = Column(String(50), nullable=False, default='ACTIVE', index=True)  # ACTIVE, BLOCKED, CLEARED
    
    # Behavioral features stored as JSON string
    behavioral_features_json = Column(Text, nullable=True)
    
    # Related/similar fingerprints (for similarity detection) stored as JSON
    related_fingerprints_json = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert database model to dictionary format compatible with ThreatFingerprint."""
        behavioral_features = {}
        if self.behavioral_features_json:
            try:
                behavioral_features = json.loads(self.behavioral_features_json)
            except json.JSONDecodeError:
                behavioral_features = {}
        
        related_fingerprints = []
        if self.related_fingerprints_json:
            try:
                related_fingerprints = json.loads(self.related_fingerprints_json)
            except json.JSONDecodeError:
                related_fingerprints = []
        
        result = {
            "fingerprint_id": self.fingerprint_id,
            "risk_score": self.risk_score,
            "user_id": self.user_id,
            "status": self.status,
            "behavioral_features": behavioral_features,
            "device_id": self.device_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        # Add related_fingerprints if present
        if related_fingerprints:
            result["related_fingerprints"] = related_fingerprints
        
        return result


# Database connection setup
def get_database_url() -> str:
    """
    Get database URL from environment variable or default to SQLite.
    
    Environment variable: DATABASE_URL
    Default: sqlite:///predictiq.db (SQLite file in project root)
    
    Examples:
    - SQLite: sqlite:///predictiq.db
    - PostgreSQL: postgresql://user:password@localhost:5432/predictiq
    """
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        return database_url
    # Default to SQLite
    db_path = os.path.join(os.path.dirname(__file__), '..', 'predictiq.db')
    return f'sqlite:///{db_path}'


# Create engine and session factory
_database_url = get_database_url()
engine = create_engine(
    _database_url,
    # SQLite-specific options
    connect_args={'check_same_thread': False} if 'sqlite' in _database_url else {},
    echo=False  # Set to True for SQL query logging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """
    Dependency function to get a database session.
    Use this in routes or other code that needs DB access.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize the database by creating all tables if they don't exist.
    Call this on application startup.
    """
    try:
        print(f"[DB] Initializing database: {_database_url}")
        Base.metadata.create_all(bind=engine)
        print("[DB] Database tables created/verified successfully")
    except UnicodeEncodeError:
        # Fallback for Windows console encoding issues
        print(f"[DB] Initializing database: {_database_url}")
        Base.metadata.create_all(bind=engine)
        print("[DB] Database tables created/verified successfully")


def get_db_session() -> Session:
    """
    Get a database session for use in synchronous code.
    Remember to call session.close() when done, or use it in a context manager.
    
    Usage:
        with get_db_session() as session:
            # use session
    """
    return SessionLocal()


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
    print("Database initialized!")

