from src.algorithm.rsa_service import SM2Service


def test_sm2_encrypt_decrypt():
    print("===== SM2 密钥生成与加解密测试 =====")
    sm2_service = SM2Service()
    sm2_service.generate_keys(password="test-password")

    ciphertext = sm2_service.encrypt_message("Hello SM2")
    plaintext = sm2_service.decrypt_message(ciphertext)

    if plaintext == "Hello SM2":
        print("测试成功：SM2 加解密结果一致！")
    else:
        raise AssertionError("测试失败：SM2 加解密结果不匹配。")


if __name__ == "__main__":
    test_sm2_encrypt_decrypt()
