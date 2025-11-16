def test_biginteger_multiply():
    # 测试4：基础乘法
    num1 = BigInteger("123")
    num2 = BigInteger("456")
    result = num1.multiply(num2)
    print(f"123 × 456 = {result}")

    # 测试5：大数乘法测试（这里简化，实际250位数字可自行构造超长字符串）
    # 示例构造两个较长数字，实际可替换为250位数字字符串
    big_num1_str = "12323" * 50  # 约250位（83*3=249）
    big_num2_str = "98787" * 50  # 约250位
    big_num1 = BigInteger(big_num1_str)
    big_num2 = BigInteger(big_num2_str)
    big_result = big_num1.multiply(big_num2)
    print(f"大数乘法结果长度：{len(str(big_result))}（预期约500位）")

    # 测试6：边界测试
    num_zero = BigInteger("0")
    num_test = BigInteger("123456789")
    # 0 + 123456789 = 123456789
    result_zero_add = num_zero.add(num_test)
    print(f"0 + 123456789 = {result_zero_add}")
    # 123456789 × 0 = 0
    result_test_zero = num_test.multiply(num_zero)
    print(f"123456789 × 0 = {result_test_zero}")
    # 123456789 × 1 = 123456789
    num_one = BigInteger("1")
    result_test_one = num_test.multiply(num_one)
    print(f"123456789 × 1 = {result_test_one}")
