import time
import gmpy2

# 使用Python内置int
start = time.time()
result1 = pow(2, 10000, 10007)  # 计算2^10000 mod 10007
time1 = time.time() - start

# 使用gmpy2
start = time.time()
result2 = gmpy2.powmod(2, 10000, 10007)
time2 = time.time() - start

print(f"Python内置: {time1:.6f}秒")
print(f"gmpy2: {time2:.6f}秒")
print(f"加速比: {time1/time2:.2f}倍")