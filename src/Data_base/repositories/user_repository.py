from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from src.Data_base.models.user import User, UserAddress
from src.Data_base.repositories.base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """用户数据访问层，包含安全查询方法"""

    def __init__(self, db: Session):
        super().__init__(User, db)

    def is_account_locked(self, user_id: int) -> bool:
        """检查账户是否被锁定"""
        try:
            user = self.get_by_id(user_id)
            if user:
                # 检查失败次数锁定
                if user.failed_attempts >= 5:
                    return True
                # 检查时间锁定
                if user.account_locked_until and user.account_locked_until > func.now():
                    return True
            return False
        except Exception as e:
            logger.error(f"检查账户锁定状态失败: {str(e)}")
            return False
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名安全查询用户"""
        try:
            user = self.db.query(User).filter(User.username == username).first()
            return user
        except Exception as e:
            print(f"查询用户失败: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱安全查询用户"""
        try:
            user = self.db.query(User).filter(
                User.email == email,
                User.is_active == True
            ).first()
            logger.info(f"查询用户邮箱: {email}")
            return user
        except Exception as e:
            logger.error(f"邮箱查询失败: {str(e)}")
            return None

    def get_user_with_addresses(self, user_id: int) -> Optional[User]:
        """获取用户及其地址信息"""
        try:
            user = self.db.query(User).options(
                joinedload(User.addresses)
            ).filter(User.user_id == user_id).first()
            logger.debug(f"获取用户地址信息: user_id={user_id}")
            return user
        except Exception as e:
            logger.error(f"获取用户地址失败: {str(e)}")
            return None

    def create_user(self, user_data: dict) -> Optional[User]:
        """创建用户"""
        try:
            user = User(**user_data)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)  # 这很重要，确保获取到数据库生成的ID
            return user
        except Exception as e:
            self.db.rollback()
            print(f"创建用户失败: {e}")
            return None

    def update_login_attempts(self, user_id: int, failed_attempts: int, locked_until=None) -> bool:
        """更新登录尝试次数（防范暴力破解）"""
        try:
            user = self.db.query(self.model).filter(self.model.user_id == user_id).first()
            if user:
                user.failed_attempts = failed_attempts
                user.account_locked_until = locked_until
                self.db.commit()
                logger.info(f"更新用户 {user_id} 登录尝试次数: {failed_attempts}")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新登录尝试失败: {str(e)}")
            return False

    def reset_login_attempts(self, user_id: int) -> bool:
        """重置登录尝试次数"""
        try:
            user = self.get_by_id(user_id)
            if user:
                user.failed_attempts = 0
                user.account_locked_until = None
                self.db.commit()
                logger.info(f"重置用户 {user_id} 登录尝试次数")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"重置登录尝试失败: {str(e)}")
            return False

    def update_last_login(self, user_id: int) -> bool:
        """更新最后登录时间"""
        try:
            from datetime import datetime
            user = self.get_by_id(user_id)
            if user:
                user.last_login = datetime.now()
                user.login_count = User.login_count + 1
                self.db.commit()
                logger.info(f"更新用户 {user_id} 最后登录时间")
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新最后登录时间失败: {str(e)}")
            return False

    def search_users(self, keyword: str, skip: int = 0, limit: int = 50) -> List[User]:
        """安全搜索用户（防SQL注入）"""
        try:
            query = self.db.query(User).filter(User.is_active == True)

            if keyword:
                # 使用LIKE但通过ORM转义，防止注入
                search_pattern = f"%{keyword}%"
                query = query.filter(
                    or_(
                        User.username.like(search_pattern),
                        User.email.like(search_pattern),
                        User.phone.like(search_pattern)
                    )
                )

            users = query.offset(skip).limit(limit).all()
            logger.info(f"搜索用户: keyword='{keyword}', 结果数: {len(users)}")
            return users
        except Exception as e:
            logger.error(f"搜索用户失败: {str(e)}")
            return []

    def get_users_by_activity(self, days: int = 30, limit: int = 100) -> List[Tuple[User, int]]:
        """获取活跃用户统计（复杂查询示例）"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import case

            active_since = datetime.now() - timedelta(days=days)

            results = self.db.query(
                User,
                func.count(case([(User.last_login >= active_since, 1)])).label('is_recent_active')
            ).outerjoin(User.orders).group_by(User.user_id).order_by(
                func.count(User.orders).desc()
            ).limit(limit).all()

            logger.info(f"获取活跃用户统计: 最近{days}天, 限制{limit}条")
            return results
        except Exception as e:
            logger.error(f"获取活跃用户统计失败: {str(e)}")
            return []


class UserAddressRepository(BaseRepository[UserAddress]):
    """用户地址数据访问层"""

    def __init__(self, db: Session):
        super().__init__(UserAddress, db)

    def get_user_addresses(self, user_id: int) -> List[UserAddress]:
        """获取用户的所有地址"""
        try:
            addresses = self.db.query(UserAddress).filter(
                UserAddress.user_id == user_id
            ).order_by(UserAddress.is_default.desc()).all()
            logger.debug(f"获取用户 {user_id} 的地址列表, 数量: {len(addresses)}")
            return addresses
        except Exception as e:
            logger.error(f"获取用户地址列表失败: {str(e)}")
            return []

    def get_default_address(self, user_id: int) -> Optional[UserAddress]:
        """获取用户的默认地址"""
        try:
            address = self.db.query(UserAddress).filter(
                UserAddress.user_id == user_id,
                UserAddress.is_default == True
            ).first()
            logger.debug(f"获取用户 {user_id} 的默认地址")
            return address
        except Exception as e:
            logger.error(f"获取默认地址失败: {str(e)}")
            return None

    def set_default_address(self, address_id: int, user_id: int) -> bool:
        """设置默认地址（事务操作）"""
        try:
            # 开始事务
            # 1. 清除该用户的所有默认地址标志
            self.db.query(UserAddress).filter(
                UserAddress.user_id == user_id,
                UserAddress.is_default == True
            ).update({'is_default': False})

            # 2. 设置新的默认地址
            address = self.get_by_id(address_id)
            if address and address.user_id == user_id:
                address.is_default = True
                self.db.commit()
                logger.info(f"设置用户 {user_id} 的默认地址: {address_id}")
                return True

            self.db.rollback()
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"设置默认地址失败: {str(e)}")
            return False