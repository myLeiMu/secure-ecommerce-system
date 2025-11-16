from src.algorithm.rsa_service import RSAService
from src.algorithm.secure_key_storage import SecureKeyStorage

def test_rotate_generate_new():
    service = RSAService()  # 实例化RSA服务
    storage = SecureKeyStorage()  # 实例化密钥存储
    new_pass = "你的新口令"  # 可以写死或通过input获取

    print("===== 测试密钥轮换：生成新密钥并保存 =====")
    storage.rotate_key(service, new_password=new_pass)
    print("完成：新密钥已生成并保存。")

if __name__ == "__main__":
    test_rotate_generate_new()