from src.Data_base.config import DB_URI
from sqlalchemy import create_engine
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
    """获取数据库会话（非上下文管理器版本）"""
    return SessionLocal()

def init_db():
    """初始化数据库表"""
    try:
        Base.metadata.create_all(bind=engine)
        logging.info("数据库表初始化成功")
    except Exception as e:
        logging.error(f"数据库表初始化失败: {str(e)}")
        raise