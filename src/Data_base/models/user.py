from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Text, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.Data_base.database import Base


class User(Base):
    __tablename__ = 'users'

    user_id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(20), index=True)
    avatar_url = Column(String(255))
    pass_word = Column(String(64), nullable=False)  # 加密后的密码
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    failed_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime)
    last_login = Column(DateTime, index=True)
    login_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    user_role = Column(String(10), default='normal')  # 身份字段：normal, admin等
    salt = Column(String(32))  # 密码盐值

    # 关系定义
    addresses = relationship("UserAddress", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username='{self.username}', email='{self.email}')>"


class UserAddress(Base):
    __tablename__ = 'user_addresses'

    address_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    recipient = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    province = Column(String(50))
    city = Column(String(50))
    district = Column(String(50))
    detail_address = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="addresses")
    orders = relationship("Order", back_populates="shipping_address")

    def __repr__(self):
        return f"<UserAddress(address_id={self.address_id}, recipient='{self.recipient}')>"