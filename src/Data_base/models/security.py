"""Persistent security state; no secrets or request bodies in audit records."""
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, DateTime
from src.Data_base.database import Base


class SecurityState(Base):
    __tablename__ = 'security_states'
    user_id = Column(BigInteger, primary_key=True)
    secret = Column(Text)
    enabled = Column(Boolean, default=False, nullable=False)
    last_step = Column(BigInteger, default=-1, nullable=False)
    recovery_hashes = Column(Text, default='[]', nullable=False)
    failures = Column(Integer, default=0, nullable=False)
    locked_until = Column(BigInteger, default=0, nullable=False)
    version = Column(Integer, default=0, nullable=False)


class LoginChallenge(Base):
    __tablename__ = 'login_challenges'
    challenge_hash = Column(String(64), primary_key=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    expires_at = Column(BigInteger, nullable=False, index=True)
    version = Column(Integer, nullable=False)
    pending_secret = Column(Text)


class AuditEvent(Base):
    __tablename__ = 'audit_events'
    event_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True)
    username = Column(String(100))
    role = Column(String(20))
    action = Column(String(100), nullable=False, index=True)
    resource = Column(String(255), nullable=False)
    result = Column(String(20), nullable=False, index=True)
    ip = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
