from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Text, Integer, DECIMAL, JSON, ForeignKey, Index, \
    CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.Data_base.database import Base


class Category(Base):
    __tablename__ = 'categories'

    category_id = Column(BigInteger, primary_key=True, autoincrement=True)
    category_name = Column(String(100), nullable=False, unique=True)
    parent_category_id = Column(BigInteger, ForeignKey('categories.category_id'))
    category_level = Column(Integer, default=1)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    # 关系
    parent = relationship("Category", remote_side=[category_id], backref="subcategories")
    products = relationship("Product", back_populates="category")

    def __repr__(self):
        return f"<Category(category_id={self.category_id}, name='{self.category_name}')>"


class Product(Base):
    __tablename__ = 'products'

    product_id = Column(BigInteger, primary_key=True, autoincrement=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    product_name = Column(String(200), nullable=False)
    description = Column(Text)
    specifications = Column(JSON)
    image_urls = Column(JSON)
    sale_price = Column(DECIMAL(10, 2), nullable=False)
    stock_quantity = Column(Integer, nullable=False)
    track_inventory = Column(Boolean, default=True)
    category_id = Column(BigInteger, ForeignKey('categories.category_id'), nullable=False, index=True)
    brand_id = Column(BigInteger, index=True)
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关系
    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")

    def __repr__(self):
        return f"<Product(product_id={self.product_id}, name='{self.product_name}', price={self.sale_price})>"


# 添加检查约束
__table_args__ = (
    CheckConstraint('sale_price >= 0', name='check_sale_price_positive'),
    CheckConstraint('stock_quantity >= 0', name='check_stock_quantity_positive'),
)