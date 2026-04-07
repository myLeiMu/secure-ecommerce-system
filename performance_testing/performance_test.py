import time
import json
import statistics
from datetime import datetime
import concurrent.futures
import csv
import os

try:
    import requests
except ImportError:
    import subprocess
    import sys

    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests


class SimplePerformanceTester:
    """简化版性能测试器"""

    def __init__(self, base_url="http://127.0.0.1:8080"):
        self.base_url = base_url
        self.results = []

        # 创建带连接池的session
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=2
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def make_request(self, method, endpoint, **kwargs):
        """发起HTTP请求"""
        url = f"{self.base_url}{endpoint}"

        # 设置默认超时
        if 'timeout' not in kwargs:
            kwargs['timeout'] = (3, 10)  # 连接3秒，读取10秒

        start = time.time()
        try:
            if method.upper() == 'GET':
                resp = self.session.get(url, **kwargs)
            elif method.upper() == 'POST':
                resp = self.session.post(url, **kwargs)
            else:
                resp = self.session.request(method, url, **kwargs)

            elapsed = time.time() - start
            success = resp.status_code in [200, 201, 204]

            self.results.append({
                'timestamp': datetime.now().isoformat(),
                'endpoint': endpoint,
                'response_time': elapsed,
                'success': success,
                'status_code': resp.status_code
            })

            return resp

        except Exception:
            elapsed = time.time() - start
            self.results.append({
                'timestamp': datetime.now().isoformat(),
                'endpoint': endpoint,
                'response_time': elapsed,
                'success': False,
                'status_code': 0
            })
            return None

    def test_concurrent(self, endpoint="/api/products", users=50):
        """并发测试 - 简化版"""
        print(f" 执行{users}并发测试: {endpoint}")

        def worker(_):
            start = time.time()
            resp = self.make_request("GET", endpoint)
            return time.time() - start, resp.status_code == 200 if resp else False

        # 使用线程池
        with concurrent.futures.ThreadPoolExecutor(max_workers=users) as executor:
            futures = [executor.submit(worker, i) for i in range(users)]
            times = [f.result()[0] for f in futures]
            successes = [f.result()[1] for f in futures]

        # 计算指标
        success_rate = sum(successes) / len(successes) if successes else 0

        return {
            'concurrent_users': users,
            'success_rate': success_rate,
            'p95_response_time': sorted(times)[int(len(times) * 0.95)] if times else 0,
            'avg_response_time': statistics.mean(times) if times else 0
        }

    def test_single_endpoint(self, endpoint, method="GET", iterations=10):
        """单端点测试"""
        print(f" 测试 {endpoint}")

        times = []
        for i in range(iterations):
            start = time.time()
            self.make_request(method, endpoint)
            times.append(time.time() - start)

            if (i + 1) % 5 == 0:
                print(f"  进度: {i + 1}/{iterations}")

        return {
            'endpoint': endpoint,
            'iterations': iterations,
            'avg_time': statistics.mean(times) if times else 0,
            'p95_time': sorted(times)[int(len(times) * 0.95)] if times else 0,
            'success_rate': sum(
                1 for r in self.results[-iterations:] if r['success']) / iterations if iterations > 0 else 0
        }

    def run_basic_tests(self):
        """运行基础测试"""
        print("=" * 50)
        print(" 开始基础性能测试")
        print("=" * 50)

        # 测试公开端点
        endpoints = [
            ("GET", "/api/products"),
            ("GET", "/api/categories"),
            ("GET", "/api/users/health"),
        ]

        results = []
        for method, endpoint in endpoints:
            result = self.test_single_endpoint(endpoint, method, 5)
            results.append(result)
            print(f" {endpoint}: {result['avg_time']:.3f}s")

        # 并发测试
        print("\n 执行并发测试")
        concurrent_result = self.test_concurrent("/api/products", 50)

        # 生成报告
        self.generate_report(results, concurrent_result)

    def generate_report(self, single_results, concurrent_result):
        """生成简单报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 计算总体指标
        all_times = [r['response_time'] for r in self.results]
        p95_time = sorted(all_times)[int(len(all_times) * 0.95)] if all_times else 0
        success_rate = sum(1 for r in self.results if r['success']) / len(self.results) if self.results else 0

        # 生成Markdown报告
        report = f"""# 性能测试报告
测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 总体指标
- 总请求数: {len(self.results)}
- 成功率: {success_rate:.1%}
- P95响应时间: {p95_time:.3f}秒

## 并发测试结果
- 并发用户: {concurrent_result['concurrent_users']}
- 成功率: {concurrent_result['success_rate']:.1%}
- P95响应时间: {concurrent_result['p95_response_time']:.3f}秒

## 单端点测试
"""

        for result in single_results:
            status = 'yes' if result['success_rate'] > 0.9 else 'no'
            report += f"- {status} {result['endpoint']}: {result['avg_time']:.3f}s\n"

        # 保存报告
        report_file = f"performance_report_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        # 保存CSV数据
        csv_file = f"performance_data_{timestamp}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['时间戳', '端点', '响应时间', '成功', '状态码'])
            for r in self.results:
                writer.writerow([
                    r['timestamp'],
                    r['endpoint'],
                    f"{r['response_time']:.3f}",
                    '是' if r['success'] else '否',
                    r['status_code']
                ])

        print(f"\n 报告已生成: {report_file}")
        print(f" 数据已保存: {csv_file}")


def main():
    """主函数"""
    tester = SimplePerformanceTester()
    tester.run_basic_tests()


if __name__ == "__main__":
    main()