from typing import List, Optional, TypeVar, Generic, Type, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from src.Data_base.database import Base
import logging

ModelType = TypeVar("ModelType", bound=Base)
logger = logging.getLogger(__name__)


class BaseRepository(Generic[ModelType]):
    """基础仓储类，提供通用的CRUD操作"""

    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get_by_id(self, id: Any) -> Optional[ModelType]:
        """根据ID获取记录"""
        try:
            result = self.db.query(self.model).filter(self.model.__table__.columns.get('id', None) == id).first()
            logger.debug(f"根据ID查询 {self.model.__name__}: {id}")
            return result
        except Exception as e:
            logger.error(f"查询 {self.model.__name__} 失败: {str(e)}")
            return None

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """获取所有记录（分页）"""
        try:
            results = self.db.query(self.model).offset(skip).limit(limit).all()
            logger.debug(f"获取所有 {self.model.__name__}, skip={skip}, limit={limit}")
            return results
        except Exception as e:
            logger.error(f"获取所有 {self.model.__name__} 失败: {str(e)}")
            return []

    def create(self, obj_in: dict) -> Optional[ModelType]:
        """创建新记录"""
        try:
            db_obj = self.model(**obj_in)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            logger.info(f"创建 {self.model.__name__} 成功: {db_obj}")
            return db_obj
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建 {self.model.__name__} 失败: {str(e)}")
            return None

    def update(self, db_obj: ModelType, obj_in: dict) -> Optional[ModelType]:
        """更新记录"""
        try:
            for field, value in obj_in.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            self.db.commit()
            self.db.refresh(db_obj)
            logger.info(f"更新 {self.model.__name__} 成功: {db_obj}")
            return db_obj
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新 {self.model.__name__} 失败: {str(e)}")
            return None

    def delete(self, id: Any) -> bool:
        """删除记录"""
        try:
            obj = self.get_by_id(id)
            if obj:
                self.db.delete(obj)
                self.db.commit()
                logger.info(f"删除 {self.model.__name__} 成功: ID={id}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除 {self.model.__name__} 失败: {str(e)}")
            return False

    def filter_by(self, **filters) -> List[ModelType]:
        """根据条件过滤记录"""
        try:
            query = self.db.query(self.model)
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)
            results = query.all()
            logger.debug(f"过滤 {self.model.__name__}: {filters}, 结果数: {len(results)}")
            return results
        except Exception as e:
            logger.error(f"过滤 {self.model.__name__} 失败: {str(e)}")
            return []

    def count(self) -> int:
        """统计记录总数"""
        try:
            count = self.db.query(self.model).count()
            logger.debug(f"统计 {self.model.__name__} 总数: {count}")
            return count
        except Exception as e:
            logger.error(f"统计 {self.model.__name__} 失败: {str(e)}")
            return 0
