import json
import os
import base64
import time
from gmssl.sm4 import CryptSM4, SM4_ENCRYPT, SM4_DECRYPT
from gmssl import sm3

class SecureKeyStorage:
    def __init__(self, filepath="asym_key_secure.json", public_path="keys/public_key.json"):
        self.filepath = filepath
        self.public_path = public_path

    @staticmethod
    def _pkcs7_pad(data: bytes, block_size: int = 16) -> bytes:
        pad_len = block_size - (len(data) % block_size)
        return data + bytes([pad_len]) * pad_len

    @staticmethod
    def _pkcs7_unpad(data: bytes, block_size: int = 16) -> bytes:
        if not data or len(data) % block_size != 0:
            raise ValueError("invalid padded data")
        pad_len = data[-1]
        if pad_len < 1 or pad_len > block_size:
            raise ValueError("invalid padding length")
        if data[-pad_len:] != bytes([pad_len]) * pad_len:
            raise ValueError("invalid padding")
        return data[:-pad_len]

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        z = (password.encode("utf-8") + salt).hex().encode("utf-8")
        key_hex = sm3.sm3_kdf(z, 16)
        return bytes.fromhex(key_hex)

    def encrypt_and_save(self, private_key_data: dict, password: str):
        salt = os.urandom(16)
        iv = os.urandom(16)
        key = self._derive_key(password, salt)
        crypt_sm4 = CryptSM4()
        crypt_sm4.set_key(key, SM4_ENCRYPT)
        data = json.dumps(private_key_data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ciphertext = crypt_sm4.crypt_cbc(iv, self._pkcs7_pad(data, 16))

        package = {
            "salt": base64.b64encode(salt).decode(),
            "iv": base64.b64encode(iv).decode(),
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
        crypt_sm4 = CryptSM4()
        crypt_sm4.set_key(key, SM4_DECRYPT)
        plaintext_padded = crypt_sm4.crypt_cbc(iv, ciphertext)
        plaintext = self._pkcs7_unpad(plaintext_padded, 16)
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

    def rotate_key(self, asymmetric_service, new_password: str = None):
        """
        密钥轮换：生成新的 SM2 密钥对并用 new_password 加密保存
        参数:
          asymmetric_service: 你的 SM2Service 实例（用于生成新密钥）
          new_password: 新口令（如果为 None，则会在函数内 input 提示输入）
        返回:
          new_private_key_dict
        """
        # 1) 备份旧的加密私钥文件（如果存在）
        if os.path.exists(self.filepath):
            self._backup_file(self.filepath)

        # 2) 生成新的密钥对
        asymmetric_service.generate_keys()
        private_key_data = asymmetric_service.export_private_key_data()

        # 更新公钥文件
        try:
            os.makedirs(os.path.dirname(self.public_path) or ".", exist_ok=True)
            with open(self.public_path, "w", encoding="utf-8") as fpub:
                json.dump(asymmetric_service.export_public_key_data(), fpub, indent=4, ensure_ascii=False)
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
