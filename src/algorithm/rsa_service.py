import json
import os
import bcrypt
import secrets
import string
from src.algorithm.rsa_core import RSAWithCRT
from src.algorithm.secure_key_storage import SecureKeyStorage

class RSAService:
    def __init__(self):
        self.rsa = RSAWithCRT()
        self.key_dir = "keys"
        os.makedirs(self.key_dir, exist_ok=True)
        self.secure_storage = SecureKeyStorage()
        # 添加密码文件路径
        self.password_file = os.path.join(self.key_dir, "auto_password.txt")

    def _generate_random_password(self):
        """生成随机密码"""
        characters = string.ascii_letters + string.digits
        return ''.join(secrets.choice(characters) for _ in range(32))

    def generate_keys(self, bits=512, password=None):
        """生成RSA密钥，自动生成随机密码"""
        self.rsa.generate_keypair(bits)
        print("[+] 已生成RSA密钥对。")

        # 保存公钥（明文）
        pub = {
            "n": self.rsa.n,
            "e": self.rsa.e
        }
        with open(os.path.join(self.key_dir, "public_key.json"), "w") as f:
            json.dump(pub, f)
        print("[+] 公钥已保存到 public_key.json。")

        # 保存加密的私钥
        private_key_data = {
            "n": self.rsa.n,
            "d": self.rsa.d,
            "p": self.rsa.p,
            "q": self.rsa.q
        }

        # 自动生成密码
        if password is None:
            password = self._generate_random_password()
            print(f"[+] 已自动生成随机密码")

        # 保存密码到文件（用于自动加载）
        with open(self.password_file, "w") as f:
            f.write(password)
        print(f"[+] 密码已保存到 {self.password_file}")

        self.secure_storage.encrypt_and_save(private_key_data, password)
        print("[+] 私钥已加密保存为 rsa_key_secure.json。")

    def load_public_key(self):
        """从文件加载公钥"""
        with open(os.path.join(self.key_dir, "public_key.json"), "r") as f:
            pub = json.load(f)
        self.rsa.n = pub["n"]
        self.rsa.e = pub["e"]
        print("[+] 公钥已加载。")

    def load_private_key_auto(self):
        """自动加载私钥（从保存的密码文件）"""
        if os.path.exists(self.password_file):
            with open(self.password_file, "r") as f:
                password = f.read().strip()
            return self.load_private_key(password)
        else:
            print("[!] 未找到密码文件，需要手动输入密码")
            return self.load_private_key(input("请输入加密私钥的口令："))

    def load_private_key(self, password):
        """解密加载加密存储的私钥"""
        private_data = self.secure_storage.decrypt_and_load(password)
        if private_data:
            self.rsa.n = private_data["n"]
            self.rsa.d = private_data["d"]
            self.rsa.p = private_data["p"]
            self.rsa.q = private_data["q"]
            print("[+] 私钥已成功解密加载。")
            return True
        else:
            print("[!] 私钥加载失败，可能是口令错误。")
            return False

    def encrypt_message(self, message: str) -> int:
        return self.rsa.encrypt(message)

    def decrypt_message(self, ciphertext: int) -> str:
        return self.rsa.decrypt_with_crt_optimized(ciphertext)


class PasswordService:
    # 类说明：安全存储与验证密码

    def hash_password(self, password: str) -> bytes:
        """注册时调用：生成哈希"""
        salt = bcrypt.gensalt()  # 自动生成随机盐
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed  # 存数据库或文件时保存这个哈希值

    def verify_password(self, password: str, hashed: bytes) -> bool:
        """登录时调用：验证密码是否匹配"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed)