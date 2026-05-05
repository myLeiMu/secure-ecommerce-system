from src.Data_base.config import DB_URI
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import logging

# 创建带连接池的引擎
engine = create_engine(
    DB_URI,
    poolclass=QueuePool,
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 最大溢出连接数
    pool_timeout=30,  # 连接超时时间(秒)
    pool_recycle=3600,  # 连接回收时间(秒)
    pool_pre_ping=True,  # 连接前ping检测
    echo=True,  # 实际环境设为False
    future=True
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()

@contextmanager
def get_db():
    """数据库会话依赖注入，确保会话正确关闭"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
        logging.info("数据库事务提交成功")
    except Exception as e:
        db.rollback()
        logging.error(f"数据库事务回滚: {str(e)}")
        raise
    finally:
        db.close()

def get_db_session():
    """获取数据库会话"""
    return SessionLocal()

def init_db():
    """初始化数据库表"""
    try:
        # 确保模型被加载到Base.metadata
        from src.Data_base.models import user, product, order  # noqa: F401

        Base.metadata.create_all(bind=engine)
        _ensure_schema_updates()
        logging.info("数据库表初始化成功")
    except Exception as e:
        logging.error(f"数据库表初始化失败: {str(e)}")
        raise


def _ensure_schema_updates():
    """
    对既有数据库执行轻量结构补齐：
    - products.seller_id
    - products.status
    - cart_items表
    """
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        if 'products' in tables:
            product_cols = {c['name'] for c in inspector.get_columns('products')}
            if 'seller_id' not in product_cols:
                conn.execute(text("ALTER TABLE products ADD COLUMN seller_id BIGINT NULL"))
                conn.execute(text("CREATE INDEX ix_products_seller_id ON products (seller_id)"))
            if 'status' not in product_cols:
                conn.execute(text("ALTER TABLE products ADD COLUMN status VARCHAR(20) DEFAULT 'active'"))
                conn.execute(text("CREATE INDEX ix_products_status ON products (status)"))

        if 'users' in tables:
            user_cols = {c['name'] for c in inspector.get_columns('users')}
            if 'bank_card_number' not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN bank_card_number VARCHAR(64) NULL DEFAULT NULL"))
            else:
                conn.execute(text("UPDATE users SET bank_card_number = NULL WHERE bank_card_number = ''"))
                conn.execute(text("ALTER TABLE users MODIFY COLUMN bank_card_number VARCHAR(64) NULL DEFAULT NULL"))

        if 'orders' in tables:
            order_cols = {c['name'] for c in inspector.get_columns('orders')}
            if 'is_deleted' not in order_cols:
                conn.execute(text("ALTER TABLE orders ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE"))
                conn.execute(text("CREATE INDEX ix_orders_is_deleted ON orders (is_deleted)"))

        if 'cart_items' not in tables:
            conn.execute(text("""
                CREATE TABLE cart_items (
                    cart_item_id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_id BIGINT NOT NULL,
                    product_id BIGINT NOT NULL,
                    quantity INT NOT NULL DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    CONSTRAINT uq_cart_user_product UNIQUE (user_id, product_id),
                    CONSTRAINT check_cart_quantity_positive CHECK (quantity > 0),
                    INDEX ix_cart_items_user_id (user_id),
                    INDEX ix_cart_items_product_id (product_id),
                    CONSTRAINT fk_cart_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    CONSTRAINT fk_cart_product FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
                )
            """))
