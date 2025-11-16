from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.Data_base.database import Base
from src.Data_base.repositories.user_repository import UserRepository
from src.utils.security import SQLInjectionValidator, InputValidator
import logging

# 设置日志
logging.basicConfig(level=logging.ERROR)
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

TEST_DATABASE_URL = "mysql+pymysql://root:Weibomysql369@localhost:3306/test_ecommerce"


class SimpleTester:
    """简单测试运行器"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.setup_database()

    def setup_database(self):
        """设置测试数据库"""
        try:
            self.engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)

            # 创建测试数据库
            from sqlalchemy import text
            conn = self.engine.connect()
            conn.execute(text("CREATE DATABASE IF NOT EXISTS test_ecommerce"))
            conn.close()

            # 重新连接到测试数据库
            self.test_engine = create_engine(
                f"{TEST_DATABASE_URL}?charset=utf8mb4",
                pool_pre_ping=True,
                echo=False
            )

        except Exception as e:
            print(f"数据库设置失败: {e}")
            raise

    def create_session(self):
        """创建测试会话"""
        Session = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)

        # 清理并创建表
        Base.metadata.drop_all(bind=self.test_engine)
        Base.metadata.create_all(bind=self.test_engine)

        return Session()

    def assert_equal(self, actual, expected, message=""):
        """断言相等"""
        if actual == expected:
            self.passed += 1
            print(f"通过: {message}")
        else:
            self.failed += 1
            print(f"失败: {message} - 期望: {expected}, 实际: {actual}")

    def assert_true(self, condition, message=""):
        """断言为真"""
        if condition:
            self.passed += 1
            print(f"通过: {message}")
        else:
            self.failed += 1
            print(f"失败: {message}")

    def assert_false(self, condition, message=""):
        """断言为假"""
        if not condition:
            self.passed += 1
            print(f"通过: {message}")
        else:
            self.failed += 1
            print(f"失败: {message}")

    def assert_none(self, value, message=""):
        """断言为None"""
        if value is None:
            self.passed += 1
            print(f"通过: {message}")
        else:
            self.failed += 1
            print(f"失败: {message} - 期望: None, 实际: {value}")

    def assert_not_none(self, value, message=""):
        """断言不为None"""
        if value is not None:
            self.passed += 1
            print(f"通过: {message}")
        else:
            self.failed += 1
            print(f"失败: {message}")

    def run_sql_injection_tests(self):
        """运行SQL注入测试"""
        print("\n" + "=" * 50)
        print("运行 SQL注入防护测试")
        print("=" * 50)

        validator = SQLInjectionValidator()

        # 测试注入攻击
        injection_attempts = [
            "admin' OR '1'='1",
            "'; DROP TABLE users; --",
            "1' UNION SELECT * FROM passwords --"
        ]

        for attempt in injection_attempts:
            result = validator.contains_sql_injection(attempt)
            self.assert_true(result, f"检测SQL注入: {attempt}")

        # 测试正常输入
        normal_inputs = ["正常商品", "user123", "test@example.com"]
        for normal in normal_inputs:
            result = validator.contains_sql_injection(normal)
            self.assert_false(result, f"正常输入通过: {normal}")

    def run_input_validation_tests(self):
        """运行输入验证测试"""
        print("\n" + "=" * 50)
        print("运行 输入验证测试")
        print("=" * 50)

        validator = InputValidator()

        # 用户名测试
        is_valid, message = validator.validate_username("user123")
        self.assert_true(is_valid, "有效用户名")

        is_valid, message = validator.validate_username("ab")
        self.assert_false(is_valid, "过短用户名")

        is_valid, message = validator.validate_username("user@name")
        self.assert_false(is_valid, "非法字符用户名")

        # 密码测试
        is_valid, message = validator.validate_password("StrongPass123!")
        self.assert_true(is_valid, "强密码")

        is_valid, message = validator.validate_password("weak")
        self.assert_false(is_valid, "弱密码")

    def run_user_repository_tests(self):
        """运行用户仓储测试"""
        print("\n" + "=" * 50)
        print("运行 用户仓储测试")
        print("=" * 50)

        session = self.create_session()
        user_repo = UserRepository(session)

        try:
            # 测试创建用户
            user_data = {
                "username": "testuser",
                "email": "test@example.com",
                "pass_word": "hashed_password",
                "is_verified": True
            }
            user = user_repo.create_user(user_data)
            self.assert_not_none(user, "创建用户")
            if user:
                self.assert_equal(user.username, "testuser", "用户名正确")
                self.assert_not_none(user.user_id, "用户ID生成")

            # 测试查询用户
            found_user = user_repo.get_user_by_username("testuser")
            self.assert_not_none(found_user, "根据用户名查询用户")

            # 测试查询不存在的用户
            not_found = user_repo.get_user_by_username("nonexistent")
            self.assert_none(not_found, "查询不存在的用户")

            # 测试安全搜索
            results = user_repo.search_users("test")
            self.assert_true(isinstance(results, list), "安全搜索返回列表")

        finally:
            session.close()

    def run_all_tests(self):
        """运行所有测试"""
        print("开始运行测试...")

        self.run_sql_injection_tests()
        self.run_input_validation_tests()
        self.run_user_repository_tests()

        # 输出总结
        print("\n" + "=" * 50)
        print("测试总结")
        print("=" * 50)
        print(f"通过: {self.passed}")
        print(f"失败: {self.failed}")
        print(f"总计: {self.passed + self.failed}")
        print(f"成功率: {self.passed / (self.passed + self.failed) * 100:.1f}%" if (self.passed + self.failed) > 0 else "成功率: N/A")

        # 清理数据库
        Base.metadata.drop_all(bind=self.test_engine)
        self.test_engine.dispose()


if __name__ == "__main__":
    tester = SimpleTester()
    tester.run_all_tests()