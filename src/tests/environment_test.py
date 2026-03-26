import sys
from src.algorithm.rsa_service import SM2Service
from src.utils.security import sm3_digest

try:
    import gmpy2
except Exception:
    gmpy2 = None
def test_environment():
    print("=== Python 环境验证 ===")
    print(f"Python 版本: {sys.version}")# 测试大整数运算
    print("\n=== 大整数运算测试 ===")
    if gmpy2:
        a = gmpy2.mpz(2**1000)
        b = gmpy2.mpz(2**500)
        result = a + b
        print(f"大整数运算测试：2^1000 + 2^500 = {len(str(result))}位数")
    else:
        print("跳过：未安装 gmpy2")
    print("\n=== SM2 功能测试 ===")
    sm2_service = SM2Service()
    sm2_service.generate_keys(password="test-password")
    print("SM2 密钥生成成功")
    # 测试哈希函数
    print("\n=== 哈希功能测试 ===")
    hash_value = sm3_digest(b"Hello World")
    print(f"SM3 哈希测试成功，结果长度：{len(hash_value)}字节")
    print("\n✅ 所有环境测试通过！")
if __name__ == "__main__":
    test_environment()
