import requests
import time
from datetime import datetime


def check_api_health():
    """检查API健康状态"""
    print("🔍 检查API健康状态...")

    endpoints = [
        ("/api/products", "商品列表"),
        ("/api/categories", "分类列表"),
        ("/api/users/health", "健康检查"),
    ]

    base_url = "http://127.0.0.1:8080"
    results = []

    for endpoint, name in endpoints:
        try:
            start = time.time()
            resp = requests.get(f"{base_url}{endpoint}", timeout=3)
            elapsed = time.time() - start

            status = "✅" if resp.status_code == 200 else "⚠️"
            results.append(f"{status} {name}: {resp.status_code} ({elapsed:.3f}s)")
            print(f"  {status} {name}: {elapsed:.3f}s")

        except Exception as e:
            results.append(f"❌ {name}: 无法访问 ({e})")
            print(f"  ❌ {name}: 无法访问")

    return results


def check_performance():
    """检查性能"""
    print("\n⚡ 检查性能...")

    base_url = "http://127.0.0.1:8080"

    # 测试响应时间
    times = []
    for i in range(5):
        try:
            start = time.time()
            requests.get(f"{base_url}/api/products", timeout=5)
            times.append(time.time() - start)
        except:
            times.append(5)  # 超时

    avg_time = sum(times) / len(times)

    # 评估性能
    if avg_time < 0.5:
        rating = "✅ 优秀"
    elif avg_time < 1.0:
        rating = "✅ 良好"
    elif avg_time < 3.0:
        rating = "⚠️  一般"
    else:
        rating = "❌ 较差"

    return avg_time, rating


def main():
    """主函数"""
    print("=" * 50)
    print("🎯 性能检查工具")
    print("=" * 50)

    # 检查健康状态
    health_results = check_api_health()

    # 检查性能
    avg_time, rating = check_performance()

    # 生成报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"performance_check_{timestamp}.txt"

    report = f"""性能检查报告
检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

健康状态:
{chr(10).join(health_results)}

性能评估:
- 平均响应时间: {avg_time:.3f}秒
- 评估结果: {rating}

建议:
"""

    if avg_time < 1.0:
        report += "系统性能良好，继续保持"
    elif avg_time < 3.0:
        report += "建议优化数据库查询和添加缓存"
    else:
        report += "需要立即优化，检查数据库连接和服务器负载"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n📄 报告已生成: {report_file}")
    print(f"📊 平均响应时间: {avg_time:.3f}秒")
    print(f"🏆 评估结果: {rating}")


if __name__ == "__main__":
    main()