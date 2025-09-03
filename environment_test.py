import sys
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
import gmpy2
def test_environment():
    print("=== Python 环境验证 ===")
    print(f"Python 版本: {sys.version}")# 测试大整数运算
    print("\n=== 大整数运算测试 ===")
    a = gmpy2.mpz(2**1000)
    b = gmpy2.mpz(2**500)
    result = a + b
    print(f"大整数运算测试：2^1000 + 2^500 = {len(str(result))}位数")
    # 测试 RSA 密钥生成
    print("\n=== RSA 功能测试 ===")
    private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
    )
    public_key = private_key.public_key()
    print("RSA 2048 位密钥生成成功")
    # 测试哈希函数
    print("\n=== 哈希功能测试 ===")
    digest = hashes.Hash(hashes.SHA256())
    digest.update(b"Hello World")
    hash_value = digest.finalize()
    print(f"SHA-256 哈希测试成功，结果长度：{len(hash_value)}字节")
    print("\n✅ 所有环境测试通过！")
if __name__ == "__main__":
    test_environment()