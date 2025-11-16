from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Text, Integer, DECIMAL, Enum, JSON, ForeignKey, \
    Index, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.Data_base.database import Base
import enum


class OrderStatus(enum.Enum):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'


class PaymentStatus(enum.Enum):
    PENDING = 'pending'
    PAID = 'paid'
    FAILED = 'failed'
    REFUNDED = 'refunded'


class FulfillmentStatus(enum.Enum):
    UNFULFILLED = 'unfulfilled'
    FULFILLED = 'fulfilled'
    PARTIALLY_FULFILLED = 'partially_fulfilled'


class PaymentMethod(enum.Enum):
    CREDIT_CARD = 'credit_card'
    ALIPAY = 'alipay'
    WECHAT_PAY = 'wechat_pay'
    BANK_TRANSFER = 'bank_transfer'


class RiskLevel(enum.Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'


class Order(Base):
    __tablename__ = 'orders'

    order_id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False, index=True)
    customer_phone = Column(String(20))
    subtotal_amount = Column(DECIMAL(10, 2), nullable=False)
    shipping_amount = Column(DECIMAL(10, 2), default=0)
    discount_amount = Column(DECIMAL(10, 2), default=0)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    order_status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, index=True)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, index=True)
    fulfillment_status = Column(Enum(FulfillmentStatus), default=FulfillmentStatus.UNFULFILLED)
    shipping_address_id = Column(BigInteger, ForeignKey('user_addresses.address_id'))
    shipping_method = Column(String(50))
    tracking_number = Column(String(100))
    order_date = Column(DateTime, default=func.now(), index=True)
    payment_due_date = Column(DateTime)
    shipped_date = Column(DateTime)
    delivered_date = Column(DateTime)
    cancelled_date = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关系
    user = relationship("User", back_populates="orders")
    shipping_address = relationship("UserAddress", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="order", uselist=False)

    def __repr__(self):
        return f"<Order(order_id={self.order_id}, number='{self.order_number}', total={self.total_amount})>"


class OrderItem(Base):
    __tablename__ = 'order_items'

    order_item_id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id = Column(BigInteger, ForeignKey('orders.order_id', ondelete='CASCADE'), nullable=False, index=True)
    product_id = Column(BigInteger, ForeignKey('products.product_id'), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    total_price = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime, default=func.now())

    # 关系
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem(order_item_id={self.order_item_id}, product_id={self.product_id}, quantity={self.quantity})>"


class Payment(Base):
    __tablename__ = 'payments'

    payment_id = Column(BigInteger, primary_key=True, autoincrement=True)
    transaction_id = Column(String(100), unique=True, index=True)
    order_id = Column(BigInteger, ForeignKey('orders.order_id'), unique=True, nullable=False, index=True)
    amount = Column(DECIMAL(10, 2), nullable=False)
    payment_method = Column(Enum(PaymentMethod))
    payment_gateway = Column(String(50))
    gateway_transaction_id = Column(String(100))
    payment_token = Column(String(255))
    card_last_four = Column(String(4))
    card_brand = Column(String(20))
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, index=True)
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.LOW)
    fraud_score = Column(Integer, default=0)
    payment_date = Column(DateTime, index=True)
    refund_date = Column(DateTime)
    captured_date = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关系
    order = relationship("Order", back_populates="payment")

    def __repr__(self):
        return f"<Payment(payment_id={self.payment_id}, amount={self.amount}, status='{self.payment_status}')>"


# 添加检查约束
for table in [Order, OrderItem, Payment]:
    if table == Order:
        table.__table_args__ = (
            CheckConstraint('subtotal_amount >= 0', name='check_order_subtotal_positive'),
            CheckConstraint('shipping_amount >= 0', name='check_shipping_amount_positive'),
            CheckConstraint('discount_amount >= 0', name='check_discount_amount_positive'),
            CheckConstraint('total_amount >= 0', name='check_total_amount_positive'),
        )
    elif table == OrderItem:
        table.__table_args__ = (
            CheckConstraint('quantity > 0', name='check_quantity_positive'),
            CheckConstraint('unit_price >= 0', name='check_unit_price_positive'),
            CheckConstraint('total_price >= 0', name='check_total_price_positive'),
        )
    elif table == Payment:
        table.__table_args__ = (
            CheckConstraint('amount >= 0', name='check_payment_amount_positive'),
            CheckConstraint('fraud_score >= 0', name='check_fraud_score_positive'),
        )