import math
import random

class BigInteger:
    def __init__(self, number_str):
        # PPT提到"基数表示：使用数组来表示大整数"
        # 我们选择列表存储，低位在前（便于进位处理）
        self.digits = [int(d) for d in reversed(number_str)]

    def __str__(self):
        # 输出时需要反转回正常顺序
        return ''.join(str(d) for d in reversed(self.digits))

    def add(self, other):
        # 实现PPT中描述的"逐位相加，处理进位"算法
        result = []  # 存储加法结果的每一位数字，采用低位在前的存储方式
        carry = 0    # 进位标志，初始值为0（没有进位）
        # 计算两个大整数中较长的位数，确保遍历所有位
        max_len = max(len(self.digits), len(other.digits))
        # 从最低位开始，逐位进行加法运算
        for i in range(max_len):
            # 初始化当前位的和，先加上上一位的进位
            digit_sum = carry
            # 如果当前索引没有超出第一个数的位数，加上对应位的值
            if i < len(self.digits):
                digit_sum += self.digits[i]
            # 如果当前索引没有超出第二个数的位数，加上对应位的值
            if i < len(other.digits):
                digit_sum += other.digits[i]
            # 计算当前位的最终值：digit_sum对10取余，得到本位应该存储的数字（0-9）
            result.append(digit_sum % 10)
            # 计算进位：digit_sum除以10的整数部分，传递给下一位
            carry = digit_sum // 10
        # 处理最高位可能产生的进位（例如：999+1=1000的情况）
        # 如果最后还有进位，需要在最高位添加这个进位值
        if carry:
            result.append(carry)
        # 将结果列表转换回BigInteger对象
        # 由于result存储的是低位在前，需要反转后连接成字符串
        return BigInteger(''.join(str(d) for d in reversed(result)))

    def multiply(self, other):
        # 实现PPT中的"逐位相乘并累加"算法，采用竖式乘法的思想
        # 初始化结果数组，长度为两个数位数之和（乘法结果的最大可能位数）
        # 例如：99 × 99 = 9801（2位×2位=4位），所以需要预留足够空间
        result_digits = [0] * (len(self.digits) + len(other.digits))
        # 实现PPT描述的竖式乘法：第一个数的每一位乘以第二个数的每一位
        # 外层循环：遍历第一个数(self)的每一位
        for i in range(len(self.digits)):
            # 内层循环：遍历第二个数(other)的每一位
            for j in range(len(other.digits)):
                # 计算当前位的乘积：self的第i位 × other的第j位
                product = self.digits[i] * other.digits[j]
                # 将乘积累加到对应的位置：i+j位置（体现了位权的相加）
                # 例如：个位×十位的结果应该放在十位上(0+1=1)
                result_digits[i + j] += product  # 注意位置偏移
        # 处理进位（PPT中提到但未详细说明的部分）
        # 上面的累加可能导致某些位上的数字大于9，需要进位处理
        carry = 0  # 初始化进位为0
        # 从低位到高位依次处理进位
        for i in range(len(result_digits)):
            # 当前位的总和 = 原始值 + 上一位的进位
            total = result_digits[i] + carry
            # 当前位的最终值：total对10取余（保留0-9的数字）
            result_digits[i] = total % 10
            # 计算传递给下一位的进位：total除以10的整数部分
            carry = total // 10
        # 去除前导零（结果数组可能在最高位有多余的0）

        # 循环条件：数组长度大于1 且 最后一位是0
        while len(result_digits) > 1 and result_digits[-1] == 0:
            result_digits.pop()  # 删除最后一位的0
        # 将结果数组转换回BigInteger对象
        # 由于result_digits是低位在前存储，需要反转后连接成字符串
        return BigInteger(''.join(str(d) for d in reversed(result_digits)))
class ChineseRemainderTheorem:
    def extended_gcd(self, a, b):
        if a == 0:  # 递归终⽌条件
            return b, 0, 1  # gcd(0,b) = b, 0*0 + 1*b = b
        # 递归调⽤
        gcd_val, x1, y1 = self.extended_gcd(b % a, a)
        # 根据递归关系计算当前层的 x, y
        x = y1 - (b // a) * x1
        y = x1
        return gcd_val, x, y

    def mod_inverse(self, a, m):
        gcd_val, x, y = self.extended_gcd(a, m)  # 使⽤扩展欧⼏⾥得算法
        if gcd_val != 1:  # 如果 gcd(a,m) != 1，则逆元不存在
            return None
        return (x % m + m) % m  # 确保结果为正数

    def solve_crt(self, remainders, moduli):
         # 检查模数是否两两互质
        for i in range(len(moduli)):
            for j in range(i + 1, len(moduli)):
                if math.gcd(moduli[i], moduli[j]) != 1:
                    raise ValueError(f"模数 {moduli[i]} 和 {moduli[j]} 不互质")
        # 计算所有模数的乘积
        M = 1
        for m in moduli:
            M *= m
        # 初始化解
        x = 0
        # 对每个同余⽅程进⾏处理
        for i in range(len(remainders)):
            ri = remainders[i]  # 当前余数
            mi = moduli[i]  # 当前模数
            Mi = M // mi  # Mi = M / mi
            # 计算 Mi 在模 mi 下的逆元
            yi = self.mod_inverse(Mi, mi)
            # 计算当前项的贡献
            term = (ri * Mi * yi) % M
            x = (x + term) % M
        return x
class RSAWithCRT:
    def __init__(self):
        self.p = None # 质数p
        self.q = None # 质数q
        self.n = None # n = p × q
        self.phi_n = None # φ(n) = (p-1)(q-1)
        self.e = None # 公钥指数
        self.d = None # 私钥指数
        self.dp = None # d mod (p-1)，⽤于CRT优化
        self.dq = None # d mod (q-1)，⽤于CRT优化
        self.qinv = None # q在模p下的逆元，⽤于CRT优化
        self.crt = ChineseRemainderTheorem() # CRT实例

    def miller_rabin_test(self, n, k=5):
        """
        Miller-Rabin素性测试
        """
        if n < 2:
            return False
        if n in (2, 3):
            return True
        if n % 2 == 0:
            return False

        # 将n-1写成d×2^s的形式
        d = n - 1
        s = 0
        while d % 2 == 0:
            d //= 2
            s += 1

        # 进行k轮测试
        for _ in range(k):
            a = random.randint(2, n - 2)
            x = mod_pow(a, d, n)

            if x == 1 or x == n - 1:
                continue
            for _ in range(s - 1):
                x = mod_pow(x, 2, n)
                if x == n - 1:
                    break
            else:
                return False
        return True
    def generate_prime(self, bits):
        """
        生成指定位数的大质数
        """
        while True:
            # 生成奇数
            num = random.getrandbits(bits)
            num |= (1 << bits - 1) | 1  # 确保是bits位数且为奇数

            if self.miller_rabin_test(num):
                return num

    def generate_keypair(self, bits=512):
        """
        ⽣成RSA密钥对
        参数:
        bits: 每个质数的位数
        """
        print(f"正在⽣成 {bits * 2} 位RSA密钥对...")
        # ⽣成两个⼤质数
        self.p = self.generate_prime(bits)
        self.q = self.generate_prime(bits)
        # 确保p和q不相等
        while self.p == self.q:
            self.q = self.generate_prime(bits)
        # 计算n和φ(n)
        self.n = self.p * self.q
        self.phi_n = (self.p - 1) * (self.q - 1)
        # 选择公钥指数e（通常选择65537）
        self.e = 65537
        while math.gcd(self.e, self.phi_n) != 1:
            self.e += 2  # 如果不互质，增加e
        # 计算私钥指数d
        self.d = self.crt.mod_inverse(self.e, self.phi_n)
        # 预计算CRT参数
        self.dp = self.d % (self.p - 1)  # d mod (p-1)
        self.dq = self.d % (self.q - 1)  # d mod (q-1)
        self.qinv = self.crt.mod_inverse(self.q, self.p)  # q^(-1) mod p

    def encrypt(self, plaintext):
        """添加加密方法"""
        if self.n is None or self.e is None:
            raise ValueError("请先生成密钥对")
        return mod_pow(plaintext, self.e, self.n)

    def decrypt_standard(self, ciphertext):
        """
        标准RSA解密（不使⽤CRT优化）
        参数:
        ciphertext: 密⽂
        返回值: 解密后的明⽂
        """
        # 标准解密: m = c^d mod n
        plaintext = mod_pow(ciphertext, self.d, self.n)
        return plaintext

    def decrypt_with_crt_optimized(self, ciphertext):
        """
        使⽤优化的CRT公式进⾏RSA解密
        参数:
        ciphertext: 密⽂
        返回值: 解密后的明⽂
        """
        # 分别计算 mod p 和 mod q
        m1 = mod_pow(ciphertext, self.dp, self.p)  # c^dp mod p
        m2 = mod_pow(ciphertext, self.dq, self.q)  # c^dq mod q
        # 使⽤优化的CRT公式
        # h = qinv × (m1 - m2) mod p
        h = (self.qinv * (m1 - m2)) % self.p
        # m = m2 + h × q
        plaintext = m2 + h * self.q
        return plaintext
def mod_pow(base, exp, mod):
    if mod == 1:
        return 0
    if exp == 0:
        return 1
    result = 1
    base = base % mod
    while exp > 0:
        if exp % 2 == 1:
            result = (result * base) % mod
        exp = exp // 2
        base = (base * base) % mod
    return result
