import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime


def setup_audit_logging(log_dir: str = "logs"):
    """设置审计日志系统"""

    # 创建日志目录
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 审计日志器
    audit_logger = logging.getLogger('audit')
    audit_logger.setLevel(logging.INFO)

    # 防止重复添加处理器
    if not audit_logger.handlers:
        # 文件处理器 - 滚动日志
        audit_file = os.path.join(log_dir, 'data_access_audit.log')
        file_handler = RotatingFileHandler(
            audit_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )

        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - '
            '[%(filename)s:%(lineno)d] - %(message)s'
        )
        file_handler.setFormatter(formatter)

        audit_logger.addHandler(file_handler)
        audit_logger.propagate = False

    # 数据库操作日志器
    db_logger = logging.getLogger('sqlalchemy.engine')
    if not db_logger.handlers:
        db_file = os.path.join(log_dir, 'database_operations.log')
        db_handler = RotatingFileHandler(
            db_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5,
            encoding='utf-8'
        )
        db_handler.setFormatter(formatter)
        db_logger.addHandler(db_handler)
        db_logger.setLevel(logging.WARNING)  # 只记录警告和错误

    return audit_logger


class DataAccessAudit:
    """数据访问审计类"""

    def __init__(self):
        self.logger = logging.getLogger('audit')

    def log_query(self, operation: str, table: str, user_id: int = None,
                  details: str = None, success: bool = True):
        """记录查询操作"""
        log_message = f"QUERY {operation} on {table}"
        if user_id:
            log_message += f" by user {user_id}"
        if details:
            log_message += f" - {details}"

        if success:
            self.logger.info(log_message)
        else:
            self.logger.warning(log_message)

    def log_data_change(self, operation: str, table: str, record_id: int,
                        user_id: int = None, old_values: dict = None,
                        new_values: dict = None):
        """记录数据变更操作"""
        log_message = f"CHANGE {operation} on {table} id={record_id}"
        if user_id:
            log_message += f" by user {user_id}"

        if old_values and new_values:
            changes = []
            for key, new_val in new_values.items():
                old_val = old_values.get(key)
                if old_val != new_val:
                    changes.append(f"{key}: {old_val} -> {new_val}")
            if changes:
                log_message += f" - Changes: {', '.join(changes)}"

        self.logger.info(log_message)

    def log_security_event(self, event_type: str, user_id: int = None,
                           ip_address: str = None, details: str = None):
        """记录安全事件"""
        log_message = f"SECURITY {event_type}"
        if user_id:
            log_message += f" user {user_id}"
        if ip_address:
            log_message += f" from {ip_address}"
        if details:
            log_message += f" - {details}"

        self.logger.warning(log_message)


# 初始化审计日志
audit_logger = setup_audit_logging()
data_audit = DataAccessAudit()