from src.algorithm.rsa_service import RSAService
from src.algorithm.rsa_service import PasswordService

def test_rsa_with_input_password():
    print("===== RSA 密钥生成与加解密测试 =====")

    # 初始化 RSA 服务
    rsa_service = RSAService()

    # 生成密钥对（用户输入口令）
    rsa_service.generate_keys(bits=256)  # 不传 password，会提示输入口令

    # 加载公钥并进行加密
    rsa_service.load_public_key()
    plaintext = 987654321
    print(f"[+] 原始明文: {plaintext}")

    ciphertext = rsa_service.rsa.encrypt(plaintext)
    print(f"[+] 加密结果: {ciphertext}")

    # 输入口令解密私钥并解密消息
    password = input("\n请输入口令以加载并解密私钥：")
    rsa_service.load_private_key(password)

    decrypted = rsa_service.rsa.decrypt_standard(ciphertext)
    print(f"[+] 解密结果: {decrypted}")

    # 检查是否一致
    if decrypted == plaintext:
        print(" 测试成功：加解密结果一致！")
    else:
        print(" 测试失败：结果不匹配。")

if __name__ == "__main__":
    test_rsa_with_input_password()

def test_password_hash_and_verify():
    print("===== 密码哈希与验证测试 =====")
    pwd_service = PasswordService()

    #  用户注册：输入密码并生成哈希
    password = input("请输入注册密码：")
    hashed = pwd_service.hash_password(password)
    print(f"[+] 已生成密码哈希（保存到数据库或文件时应保存此哈希）:")
    print(hashed)

    #  用户登录：输入密码并验证
    verify_input = input("\n请输入登录时的密码以验证：")
    is_valid = pwd_service.verify_password(verify_input, hashed)

    #  输出验证结果
    if is_valid:
        print(" 密码验证成功！登录通过。")
    else:
        print(" 密码验证失败！密码错误。")

if __name__ == "__main__":
    test_password_hash_and_verify()