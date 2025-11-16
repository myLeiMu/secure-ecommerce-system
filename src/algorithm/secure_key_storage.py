import json
import os
import base64
import time
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

class SecureKeyStorage:
    def __init__(self, filepath="rsa_key_secure.json", public_path="keys/public_key.json"):
        self.filepath = filepath
        self.public_path = public_path

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """从用户口令派生 AES 密钥（PBKDF2）"""
        return PBKDF2(password.encode('utf-8'), salt, dkLen=32, count=200000)

    def encrypt_and_save(self, private_key_data: dict, password: str):
        """用 AES-CBC 对私钥 JSON 序列化后加密并保存到文件"""
        salt = get_random_bytes(16)
        key = self._derive_key(password, salt)
        cipher = AES.new(key, AES.MODE_CBC)
        data = json.dumps(private_key_data).encode("utf-8")
        ciphertext = cipher.encrypt(pad(data, AES.block_size))

        package = {
            "salt": base64.b64encode(salt).decode(),
            "iv": base64.b64encode(cipher.iv).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode(),
        }

        # 确保目录存在
        os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)

        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(package, f, indent=4)
        print(f"[+] 已安全保存加密的私钥到 {self.filepath}")

    def decrypt_and_load(self, password: str) -> dict:
        """解密并返回私钥数据字典；若口令错误会抛出异常"""
        with open(self.filepath, "r", encoding="utf-8") as f:
            package = json.load(f)

        salt = base64.b64decode(package["salt"])
        iv = base64.b64decode(package["iv"])
        ciphertext = base64.b64decode(package["ciphertext"])

        key = self._derive_key(password, salt)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
        data = json.loads(plaintext.decode("utf-8"))
        return data

    def _backup_file(self, src_path: str) -> str:
        """把现有文件备份到同目录下，返回备份文件名"""
        if not os.path.exists(src_path):
            return ""
        ts = int(time.time())
        dirp, name = os.path.split(src_path)
        backup_name = f"{name}.backup.{ts}"
        backup_path = os.path.join(dirp, backup_name)
        os.rename(src_path, backup_path)
        print(f"[+] 已备份 {src_path} -> {backup_path}")
        return backup_path

    def rotate_key(self, rsa_service, new_password: str = None):
        """
        密钥轮换：生成新的 RSA 密钥对并用 new_password 加密保存
        参数:
          rsa_service: 你的 RSAService 实例（用于生成新密钥）
          new_password: 新口令（如果为 None，则会在函数内 input 提示输入）
        返回:
          new_private_key_dict
        """
        # 1) 备份旧的加密私钥文件（如果存在）
        if os.path.exists(self.filepath):
            self._backup_file(self.filepath)

        # 2) 生成新的密钥对
        rsa_service.generate_keys()  # 可传 bits 参数到 generate_keys
        rsa_obj = getattr(rsa_service, "rsa", rsa_service)
        n = getattr(rsa_obj, "n", None)
        e = getattr(rsa_obj, "e", None)
        d = getattr(rsa_obj, "d", None)
        if n is None or d is None:
            raise RuntimeError("无法从 rsa_service 中获取 n/d，检查 RSAService 实现。")
        private_key_data = {"n": n, "e": e, "d": d}

        # 更新公钥文件
        try:
            os.makedirs(os.path.dirname(self.public_path) or ".", exist_ok=True)
            with open(self.public_path, "w", encoding="utf-8") as fpub:
                json.dump({"n": n, "e": e}, fpub, indent=4)
            print(f"[+] 公钥已写入 {self.public_path}")
        except Exception as ex:
            print("[!] 写入公钥文件失败：", ex)

        # 3) 确保 new_password 可用
        if new_password is None:
            new_password = input("请输入用于加密新私钥的口令：")

        # 4) 加密并保存新私钥
        self.encrypt_and_save(private_key_data, new_password)
        print("[+] 新密钥已生成并加密保存，轮换完成。")

        return private_key_data
