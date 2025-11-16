import requests
import json
import time
import random
from datetime import datetime

BASE_URL = "http://127.0.0.1:8080"


class APITester:
    def __init__(self):
        self.test_results = []
        self.current_token = None
        self.test_users = []  # 存储测试用户

    def print_test_result(self, test_name, success, response=None, expected=None):
        """打印测试结果并记录"""
        status = "通过" if success else "失败"
        result = {
            "test_name": test_name,
            "status": status,
            "success": success,
            "status_code": response.status_code if response else None,
            "response": response.text[:200] + "..." if response and len(
                response.text) > 200 else response.text if response else None,
            "expected": expected
        }
        self.test_results.append(result)

        print(f"{test_name}: {status}")
        if response:
            print(f"   状态码: {response.status_code}")
            if expected:
                print(f"   预期: {expected}")
            print(f"   响应: {response.text[:100]}...")
        print("-" * 60)

    def create_test_user(self):
        """创建测试用户，不重复注册"""
        timestamp = int(time.time())
        username = f"testuser_{timestamp}"

        url = f"{BASE_URL}/api/users/register"
        data = {
            "username": username,
            "password": "Test123456!",
            "phone": f"138{random.randint(10000000, 99999999)}",
            "code": "123456",
            "email": f"test{timestamp}@example.com"
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200 and response.json().get("code") == 0:
                self.test_users.append(username)
                return username
        except Exception:
            pass
        return None

    def login_test_user(self, username=None, password="Test123456!"):
        """登录测试用户"""
        if not username and self.test_users:
            username = self.test_users[-1]

        url = f"{BASE_URL}/api/auth/login"
        data = {
            "username": username,
            "password": password
        }

        try:
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200 and response.json().get("code") == 0:
                self.current_token = response.json().get("data", {}).get("token")
                return self.current_token
        except Exception:
            pass
        return None

    def test_1_normal_registration(self):
        """测试用例1: 正常用户注册"""
        print("测试用例1: 正常用户注册")

        username = self.create_test_user()
        success = username is not None
        self.print_test_result("正常用户注册", success, None, "成功创建测试用户")
        return username

    def test_2_duplicate_username(self):
        """测试用例2: 重复用户名注册"""
        print("测试用例2: 重复用户名注册")

        url = f"{BASE_URL}/api/users/register"
        data = {
            "username": "duplicate_user_test",
            "password": "Test123456!",
            "phone": "13800138001",
            "code": "123456"
        }

        # 第一次注册
        response1 = requests.post(url, json=data, timeout=10)

        # 第二次注册相同用户名
        response2 = requests.post(url, json=data, timeout=10)

        success = response2.status_code in [400, 409]
        self.print_test_result("重复用户名注册", success, response2, "状态码400或409")

    def test_3_missing_required_fields(self):
        """测试用例3: 缺失必填字段"""
        print("测试用例3: 缺失必填字段")

        url = f"{BASE_URL}/api/users/register"
        # 缺少password字段
        data = {
            "username": "testuser_missing",
            "phone": "13800138002",
            "code": "123456"
        }

        response = requests.post(url, json=data, timeout=10)
        success = response.status_code == 400
        self.print_test_result("缺失必填字段", success, response, "状态码400")

    def test_4_user_login_success(self):
        """测试用例4: 用户登录成功"""
        print("测试用例4: 用户登录成功")

        # 使用已创建的测试用户，避免重复注册
        if not self.test_users:
            username = self.create_test_user()
        else:
            username = self.test_users[0]

        token = self.login_test_user(username)
        success = token is not None
        self.print_test_result("用户登录成功", success, None, "成功获取token")
        return token

    def test_5_user_login_failure(self):
        """测试用例5: 用户登录失败（错误密码）"""
        print("测试用例5: 用户登录失败")

        url = f"{BASE_URL}/api/auth/login"
        data = {
            "username": "nonexistent_user_123",
            "password": "WrongPassword123!"
        }

        response = requests.post(url, json=data, timeout=10)
        success = response.status_code == 401
        self.print_test_result("用户登录失败", success, response, "状态码401")

    def test_6_jwt_authentication(self):
        """测试用例6: JWT认证访问受保护接口"""
        print("测试用例6: JWT认证访问")

        # 确保有token
        if not self.current_token:
            self.test_4_user_login_success()

        url = f"{BASE_URL}/api/users/profile"
        headers = {
            "Authorization": f"Bearer {self.current_token}"
        }

        response = requests.get(url, headers=headers, timeout=10)
        success = response.status_code == 200
        self.print_test_result("JWT认证访问", success, response, "状态码200")

    def test_7_invalid_jwt_token(self):
        """测试用例7: 无效JWT令牌访问"""
        print("测试用例7: 无效JWT令牌访问")

        url = f"{BASE_URL}/api/users/profile"
        headers = {
            "Authorization": "Bearer invalid_token_123456"
        }

        response = requests.get(url, headers=headers, timeout=10)
        success = response.status_code == 401
        self.print_test_result("无效JWT令牌访问", success, response, "状态码401")

    def test_8_sql_injection_protection(self):
        """测试用例8: SQL注入防护"""
        print("测试用例8: SQL注入防护")

        # 测试用户注册接口的SQL注入防护
        url = f"{BASE_URL}/api/users/register"

        sql_test_cases = [
            {
                "name": "单引号闭合攻击",
                "data": {
                    "username": "normal_user_123",
                    "password": "Test123!",
                    "phone": "13800138001",
                    "code": "123456",
                    "email": "test' OR '1'='1@example.com"
                }
            },
            {
                "name": "注释符攻击",
                "data": {
                    "username": "test' --",
                    "password": "Test123!",
                    "phone": "13800138002",
                    "code": "123456"
                }
            },
            {
                "name": "联合查询攻击",
                "data": {
                    "username": "test' UNION SELECT",
                    "password": "Test123!",
                    "phone": "13800138003",
                    "code": "123456"
                }
            },
            {
                "name": "DROP表攻击",
                "data": {
                    "username": "test'; DROP TABLE users --",
                    "password": "Test123!",
                    "phone": "13800138004",
                    "code": "123456"
                }
            },
            {
                "name": "双引号攻击",
                "data": {
                    "username": "admin\" OR \"1\"=\"1",
                    "password": "Test123!",
                    "phone": "13800138005",
                    "code": "123456"
                }
            }
        ]

        blocked_count = 0
        total_cases = len(sql_test_cases)
        failed_cases = []

        for test_case in sql_test_cases:
            print(f"   测试: {test_case['name']}")
            response = requests.post(url, json=test_case['data'], timeout=10)

            # 检查是否被SQL注入检测拦截（400状态码）
            if response.status_code == 400:
                blocked_count += 1
                print(f"     被SQL注入检测拦截")
            else:
                failed_cases.append(test_case['name'])
                print(f"     未被拦截 (状态码: {response.status_code})")
        # 要求所有攻击都必须被拦截
        success = blocked_count == total_cases
        details = f"拦截了 {blocked_count}/{total_cases} 个SQL注入攻击"

        if not success and failed_cases:
            details += f"，未拦截: {', '.join(failed_cases)}"

        self.print_test_result("SQL注入防护", success, None, details)
    def test_9_product_list_public_access(self):
        """测试用例9: 商品列表公开访问"""
        print("测试用例9: 商品列表公开访问")

        url = f"{BASE_URL}/api/products"

        response = requests.get(url, timeout=10)
        success = response.status_code == 200 and response.json().get("code") == 0

        # 测试搜索功能
        search_url = f"{BASE_URL}/api/products?keyword=手机"
        response_search = requests.get(search_url, timeout=10)
        success_search = response_search.status_code == 200

        overall_success = success and success_search
        self.print_test_result("商品列表公开访问", overall_success, response, "状态码200, 支持搜索")

    def test_10_rate_limiting(self):
        """测试用例10: 频率限制测试"""
        print("测试用例10: 频率限制测试")

        url = f"{BASE_URL}/api/users/profile"  # 需要认证的接口

        # 发送快速连续请求
        results = []
        for i in range(5):
            start_time = time.time()
            response = requests.get(url, timeout=5)  # 不带token
            response_time = time.time() - start_time
            results.append({
                "request": i + 1,
                "status_code": response.status_code,
                "response_time": response_time
            })
            time.sleep(0.2)  # 稍微延迟避免被限流

        # 检查是否有请求被限流（应该没有，因为间隔较大）
        limited_requests = [r for r in results if r["status_code"] == 429]
        success = len(limited_requests) == 0

        print(f"   请求详情: {results}")
        self.print_test_result("频率限制测试", success, None, "正常请求不被误限流")

    def test_11_response_format_consistency(self):
        """测试用例11: 响应格式一致性"""
        print("测试用例11: 响应格式一致性")

        test_endpoints = [
            {"method": "GET", "url": f"{BASE_URL}/api/products"},
            {"method": "POST", "url": f"{BASE_URL}/api/auth/login", "data": {"username": "test", "password": "test"}}
        ]

        all_correct_format = True
        for endpoint in test_endpoints:
            if endpoint["method"] == "GET":
                response = requests.get(endpoint["url"], timeout=10)
            else:
                response = requests.post(endpoint["url"], json=endpoint.get("data"), timeout=10)

            if response.status_code in [200, 400, 401]:
                try:
                    response_data = response.json()
                    required_fields = ["code", "message", "data", "timestamp"]
                    has_all_fields = all(field in response_data for field in required_fields)

                    if not has_all_fields:
                        all_correct_format = False
                        print(f"   格式错误端点: {endpoint['url']}")
                except json.JSONDecodeError:
                    all_correct_format = False
                    print(f"   JSON解析失败: {endpoint['url']}")

        self.print_test_result("响应格式一致性", all_correct_format, None, "所有接口格式统一")

    def test_12_cors_support(self):
        """测试用例12: CORS跨域支持"""
        print("测试用例12: CORS跨域支持")

        url = f"{BASE_URL}/api/products"
        headers = {
            "Origin": "http://localhost:3000"
        }

        response = requests.get(url, headers=headers, timeout=10)

        # 检查CORS头
        cors_headers = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods",
            "Access-Control-Allow-Headers"
        ]

        has_cors_headers = any(header in response.headers for header in cors_headers)
        success = has_cors_headers and response.status_code == 200

        print(f"   响应头: {dict(response.headers)}")
        self.print_test_result("CORS跨域支持", success, response, "包含CORS头信息")

    def generate_test_report(self):
        """生成测试报告"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests

        report = f"""
API测试报告

测试概览
- 测试时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- 测试环境: {BASE_URL}
- 总测试用例: {total_tests}个
- 通过用例: {passed_tests}个
- 失败用例: {failed_tests}个
- 通过率: {(passed_tests / total_tests) * 100:.1f}%

详细测试结果

| 序号 | 测试项目 | 状态 | 状态码 | 说明 |
|------|----------|------|--------|------|
"""

        for i, result in enumerate(self.test_results, 1):
            status_icon = "[PASS]" if result["success"] else "[FAIL]"
            report += f"| {i} | {result['test_name']} | {status_icon} | {result['status_code'] or 'N/A'} | {result['expected']} |\n"

        report += """
测试结论
"""
        if failed_tests == 0:
            report += "所有测试用例通过，API服务运行正常！"
        else:
            report += f"有{failed_tests}个测试用例失败，需要检查相关功能。"

        with open("API测试报告.md", "w", encoding="utf-8") as f:
            f.write(report)

        print(f"测试报告已生成: API测试报告.md")
        print(f"测试结果: {passed_tests}/{total_tests} 通过")

    def run_all_tests(self):
        """运行所有测试用例"""
        print("开始执行API测试")
        print("=" * 70)

        # 按顺序执行测试用例，避免重复调用
        self.test_1_normal_registration()
        self.test_2_duplicate_username()
        self.test_3_missing_required_fields()
        self.test_4_user_login_success()
        self.test_5_user_login_failure()
        self.test_6_jwt_authentication()
        self.test_7_invalid_jwt_token()
        self.test_8_sql_injection_protection()
        self.test_9_product_list_public_access()
        self.test_10_rate_limiting()
        self.test_11_response_format_consistency()
        self.test_12_cors_support()

        print("=" * 70)
        self.generate_test_report()


if __name__ == "__main__":
    tester = APITester()
    tester.run_all_tests()