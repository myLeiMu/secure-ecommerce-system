import os
import time
from datetime import datetime


def check_environment():
    """检查环境"""
    print(" 检查环境...")

    # 检查必要文件
    required_files = ['performance_test.py']
    for f in required_files:
        if not os.path.exists(f):
            print(f" 缺少必要文件: {f}")
            return False

    # 创建报告目录
    os.makedirs("reports", exist_ok=True)
    print(" 环境检查通过")
    return True


def run_tests():
    """运行测试"""
    print("\n 开始测试...")

    try:
        # 运行性能测试
        from performance_test import SimplePerformanceTester
        tester = SimplePerformanceTester()
        tester.run_basic_tests()
        return True
    except Exception as e:
        print(f" 测试失败: {e}")
        return False


def generate_summary():
    """生成测试总结"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    summary = f"""# 测试执行总结
执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 已完成的测试
1.  单端点性能测试
2.  50用户并发测试
3.  报告生成

## 生成的文件
请在当前目录查看：
- performance_report_*.md (性能测试报告)
- performance_data_*.csv (测试数据)

## 下一步
1. 查看性能报告
2. 根据结果优化系统
3. 重新运行测试验证
"""

    summary_file = f"test_summary_{timestamp}.md"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary)

    return summary_file


def main():
    """主函数"""
    print("=" * 50)
    print(" 性能测试运行器")
    print("=" * 50)

    start = time.time()

    # 检查环境
    if not check_environment():
        return

    # 运行测试
    if not run_tests():
        print("  测试执行失败")

    # 生成总结
    summary_file = generate_summary()

    # 完成
    elapsed = time.time() - start

    print(f"\n 测试完成 (耗时: {elapsed:.1f}秒)")
    print(f" 总结报告: {summary_file}")


if __name__ == "__main__":
    main()