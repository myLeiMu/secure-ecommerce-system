import requests
import time
import threading
from collections import deque


class SimpleMonitor:
    """简单性能监控器"""

    def __init__(self, base_url="http://127.0.0.1:8080"):
        self.base_url = base_url
        self.response_times = deque(maxlen=100)  # 记录最近100次响应时间
        self.errors = deque(maxlen=100)
        self.running = False

    def check_endpoint(self, endpoint="/api/products"):
        """检查单个端点"""
        start = time.time()
        try:
            resp = requests.get(f"{self.base_url}{endpoint}", timeout=5)
            elapsed = time.time() - start

            self.response_times.append(elapsed)

            if resp.status_code == 200:
                return True, elapsed
            else:
                self.errors.append(f"HTTP {resp.status_code}")
                return False, elapsed

        except Exception as e:
            self.errors.append(str(e))
            return False, time.time() - start

    def start_monitoring(self, interval=5):
        """开始监控"""
        self.running = True
        print(f" 开始监控 (间隔: {interval}秒)")

        def monitor_loop():
            while self.running:
                success, elapsed = self.check_endpoint()

                status = "yes" if success else "no"
                color = "\033[92m" if elapsed < 1 else "\033[93m" if elapsed < 3 else "\033[91m"

                print(f"{status} {color}响应: {elapsed:.3f}s\033[0m")

                # 显示统计信息
                if len(self.response_times) >= 10:
                    avg = sum(self.response_times) / len(self.response_times)
                    print(f"   平均: {avg:.3f}s | 最近10次: {list(self.response_times)[-10:]}")

                time.sleep(interval)

        # 启动监控线程
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()

        return thread

    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        print("  停止监控")

        # 生成监控报告
        if self.response_times:
            self.generate_report()

    def generate_report(self):
        """生成监控报告"""
        if not self.response_times:
            print("  无监控数据")
            return

        avg_time = sum(self.response_times) / len(self.response_times)
        max_time = max(self.response_times)
        min_time = min(self.response_times)

        error_rate = len(self.errors) / len(self.response_times) if self.response_times else 0

        print("\n 监控报告")
        print("=" * 40)
        print(f"总检查次数: {len(self.response_times)}")
        print(f"平均响应时间: {avg_time:.3f}秒")
        print(f"最快响应: {min_time:.3f}秒")
        print(f"最慢响应: {max_time:.3f}秒")
        print(f"错误率: {error_rate:.1%}")

        if self.errors:
            print(f"最近错误: {list(self.errors)[-5:]}")


def main():
    """主函数"""
    monitor = SimpleMonitor()

    try:
        print(" 性能监控启动 (按Ctrl+C停止)")
        monitor.start_monitoring(interval=3)

        # 保持主线程运行
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        monitor.stop_monitoring()
        print("\n 监控已停止")


if __name__ == "__main__":
    main()