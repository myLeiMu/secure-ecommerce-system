import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.algorithm.RSA import*
def test_biginteger():
    # 测试1：基础加法（验证PPT理论）
    # 创建第⼀个⼤整数对象，值为123456789
    test1 = BigInteger("123456789")
    # 创建第⼆个⼤整数对象，值为987654321
    test2 = BigInteger("987654321")
    # 调⽤add⽅法执⾏⼤整数加法运算
    result = test1.add(test2)
    # 输出加法结果，验证是否等于期望值1111111110
    print(f"123456789 + 987654321 = {result}")  # 期望：1111111110
    # 测试2：连续进位挑战
    # 创建⼀个9位全为9的⼤整数，这是连续进位的经典测试⽤例
    test3 = BigInteger("999999999")
    # 创建⼤整数1，⽤于测试连续进位（999999999+1会在每⼀位都产⽣进位）
    test4 = BigInteger("1")
    # 执⾏加法运算，测试连续进位处理能⼒
    result2 = test3.add(test4)
    # 输出结果，验证连续进位是否正确处理（应该得到1000000000）
    print(f"999999999 + 1 = {result2}")  # 期望：1000000000
    # 测试3：⼤数测试（500位数）
    # 构造第⼀个500位⼤数：1后⾯跟499个2，即122222...222（500位）
    big1 = BigInteger("1" + "2" * 499)  # 500位数
    # 构造第⼆个500位⼤数：9后⾯跟499个8，即988888...888（500位）
    big2 = BigInteger("9" + "8" * 499)  # 500位数
    # 执⾏两个500位数的加法运算，测试算法对超⼤数字的处理能⼒
    result3 = big1.add(big2)
    # 输出结果的位数，验证⼤数运算的正确性（应该是500位或501位）
    print(f"⼤数加法位数：{len(str(result3))}")
def pow_test():
    # 测试⽤例1：验证PPT例⼦
    assert mod_pow(3, 13, 7) == 3
    # 测试⽤例2：边界情况
    assert mod_pow(5, 0, 7) == 1  # 任何数的0次幂
    assert mod_pow(5, 1, 7) == 5  # 1次幂
    assert mod_pow(0, 5, 7) == 0  # 0的任何正数次幂
    # 测试⽤例3：⼤数测试
    large_exp = 2 ** 1000  # 1024位指数！
    result = mod_pow(2, large_exp, 1000000007)
    print(f"2^(2^1000) mod 1000000007 = {result}")
def comprehensive_test():
    """
    综合测试：结合⼤整数运算和模幂运算
    """
    print("=== 综合测试：为RSA算法做准备 ===")
    # 模拟RSA计算中的⼤数运算
    p, q = 61, 53 # 两个质数
    n = p * q # RSA模数
    # 测试⼤整数乘法
    big_p = BigInteger(str(p))
    big_q = BigInteger(str(q))
    big_n = big_p.multiply(big_q)
    print(f"⼤整数乘法：{p} × {q} = {big_n}")
    # 测试模幂运算（模拟RSA加密）
    message = 42
    e = 17 # 公钥指数
    ciphertext = mod_pow(message, e, n)
    print(f"模拟RSA加密：{message}^{e} mod {n} = {ciphertext}")
    # 验证解密（需要计算私钥d）
    # d = 2753 # 预计算的私钥
    # decrypted = mod_pow_manual(ciphertext, d, n)
    # print(f"模拟RSA解密：{ciphertext}^{d} mod {n} = {decrypted}")
def test_rsa_with_crt():
    # 测试代码
    rsa = RSAWithCRT()
    rsa.generate_keypair(bits=64)  # 使用较小的位数以便快速测试

    # 测试消息
    original_message = 123456789

    # 加密
    ciphertext = rsa.encrypt(original_message)
    print(f"原始消息: {original_message}")
    print(f"加密后: {ciphertext}")

    # 解密测试1: 标准方法
    start_time = time.time()
    decrypted_standard = rsa.decrypt_standard(ciphertext)
    standard_time = time.time() - start_time

    # 解密测试2: CRT方法
    start_time = time.time()
    decrypted_crt = rsa.decrypt_with_crt_optimized(ciphertext)
    crt_time = time.time() - start_time

    # 验证结果
    print(f"标准解密结果: {decrypted_standard}")
    print(f"CRT解密结果: {decrypted_crt}")
    print(f"解密正确性: {decrypted_standard == decrypted_crt == original_message}")

    # 性能对比
    speedup = standard_time / crt_time if crt_time > 0 else float('inf')
    print(f"标准解密时间: {standard_time:.6f}秒")
    print(f"CRT解密时间: {crt_time:.6f}秒")
    print(f"CRT加速比: {speedup:.2f}x")

test_biginteger()
pow_test()
comprehensive_test()
test_rsa_with_crt()