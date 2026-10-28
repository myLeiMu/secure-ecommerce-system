from src.algorithm.rsa_service import SM2Service
from src.algorithm.secure_key_storage import SecureKeyStorage
from tempfile import TemporaryDirectory
import secrets

def test_rotate_generate_new():
    with TemporaryDirectory() as key_dir:
        service = SM2Service(key_dir)
        storage = service.secure_storage
        print("===== 在临时目录测试密钥轮换 =====")
        storage.rotate_key(service, new_password=secrets.token_urlsafe(24))
        print("完成：测试密钥已生成并保存，不修改业务密钥。")

if __name__ == "__main__":
    test_rotate_generate_new()
