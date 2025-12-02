import requests
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime


def quick_performance_test():
    """快速性能测试"""
    print(" 快速性能测试开始")

    base_url = "http://127.0.0.1:8080"
    results = []

    # 1. 测试单个端点
    print(" 测试单个端点...")

    endpoints = [
        "/api/products",
        "/api/categories",
        "/api/users/health"
    ]

    for endpoint in endpoints:
        times = []
        for _ in range(3):  # 每个端点测3次
            start = time.time()
            try:
                resp = requests.get(f"{base_url}{endpoint}", timeout=5)
                times.append(time.time() - start)
            except:
                times.append(5)  # 超时

        avg_time = sum(times) / len(times)
        results.append(f"{endpoint}: {avg_time:.3f}s")
        print(f"  {endpoint}: {avg_time:.3f}s")

    # 2. 快速并发测试
    print("\n 快速并发测试 (10用户)...")

    def make_request(_):
        start = time.time()
        try:
            requests.get(f"{base_url}/api/products", timeout=5)
            return time.time() - start, True
        except:
            return 5, False

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request, i) for i in range(10)]
        times = [f.result()[0] for f in futures]
        success = sum(1 for f in futures if f.result()[1])

    concurrent_result = {
        'success_rate': success / 10,
        'avg_time': sum(times) / len(times),
        'max_time': max(times)
    }

    # 3. 生成简要报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"quick_test_{timestamp}.txt"

    report = f"""快速性能测试报告
测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

单端点响应时间:
{chr(10).join(results)}

并发测试 (10用户):
- 成功率: {concurrent_result['success_rate']:.1%}
- 平均响应: {concurrent_result['avg_time']:.3f}s
- 最大响应: {concurrent_result['max_time']:.3f}s

结论:
"""

    if concurrent_result['avg_time'] < 1.0:
        report += " 性能良好"
    elif concurrent_result['avg_time'] < 3.0:
        report += "  性能一般，建议优化"
    else:
        report += " 性能较差，需要优化"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n 报告已生成: {report_file}")
    return True


if __name__ == "__main__":
    quick_performance_test()