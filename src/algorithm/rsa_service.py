import json
import os
import secrets
import string
from src.algorithm.secure_key_storage import SecureKeyStorage
from gmssl import sm2, func
import base64

class SM2Service:
    def __init__(self):
        self.key_dir = "keys"
        os.makedirs(self.key_dir, exist_ok=True)
        self.secure_storage = SecureKeyStorage(
            filepath=os.path.join(self.key_dir, "sm2_key_secure.json"),
            public_path=os.path.join(self.key_dir, "public_key.json"),
        )
        self.password_file = os.path.join(self.key_dir, "auto_password.txt")
        self.private_key_hex = None
        self.public_key_hex = None
        self._sm2 = None

    def _generate_random_password(self):
        """生成随机密码"""
        characters = string.ascii_letters + string.digits
        return ''.join(secrets.choice(characters) for _ in range(32))

    def generate_keys(self, password=None):
        private_key_hex = func.random_hex(64)
        sm2_crypt = sm2.CryptSM2(public_key="", private_key=private_key_hex)
        public_key_hex = sm2_crypt._kg(int(private_key_hex, 16), sm2_crypt.ecc_table["g"])
        self.private_key_hex = private_key_hex
        self.public_key_hex = public_key_hex
        self._sm2 = sm2.CryptSM2(public_key=public_key_hex, private_key=private_key_hex)
        print("[+] 已生成SM2密钥对。")

        with open(os.path.join(self.key_dir, "public_key.json"), "w", encoding="utf-8") as f:
            json.dump({"public_key": public_key_hex}, f, ensure_ascii=False, indent=4)
        print("[+] 公钥已保存到 public_key.json。")

        private_key_data = {"private_key": private_key_hex, "public_key": public_key_hex}

        # 自动生成密码
        if password is None:
            password = self._generate_random_password()
            print(f"[+] 已自动生成随机密码")

        # 保存密码到文件（用于自动加载）
        with open(self.password_file, "w", encoding="utf-8") as f:
            f.write(password)
        print(f"[+] 密码已保存到 {self.password_file}")

        self.secure_storage.encrypt_and_save(private_key_data, password)
        print("[+] 私钥已加密保存为 sm2_key_secure.json。")

    def load_public_key(self):
        """从文件加载公钥"""
        with open(os.path.join(self.key_dir, "public_key.json"), "r", encoding="utf-8") as f:
            pub = json.load(f)
        self.public_key_hex = pub["public_key"]
        self._sm2 = sm2.CryptSM2(public_key=self.public_key_hex, private_key=self.private_key_hex or "")
        print("[+] 公钥已加载。")

    def load_private_key_auto(self):
        """自动加载私钥（从保存的密码文件）"""
        if os.path.exists(self.password_file):
            with open(self.password_file, "r", encoding="utf-8") as f:
                password = f.read().strip()
            return self.load_private_key(password)
        else:
            print("[!] 未找到密码文件，需要手动输入密码")
            return self.load_private_key(input("请输入加密私钥的口令："))

    def load_private_key(self, password):
        """解密加载加密存储的私钥"""
        private_data = self.secure_storage.decrypt_and_load(password)
        if private_data:
            self.private_key_hex = private_data["private_key"]
            self.public_key_hex = private_data["public_key"]
            self._sm2 = sm2.CryptSM2(public_key=self.public_key_hex, private_key=self.private_key_hex)
            print("[+] 私钥已成功解密加载。")
            return True
        else:
            print("[!] 私钥加载失败，可能是口令错误。")
            return False

    def export_public_key_data(self) -> dict:
        if not self.public_key_hex:
            raise RuntimeError("public key not loaded")
        return {"public_key": self.public_key_hex}

    def export_private_key_data(self) -> dict:
        if not self.private_key_hex or not self.public_key_hex:
            raise RuntimeError("private key not loaded")
        return {"private_key": self.private_key_hex, "public_key": self.public_key_hex}

    @staticmethod
    def _to_bytes(message) -> bytes:
        if isinstance(message, bytes):
            return message
        if isinstance(message, str):
            return message.encode("utf-8")
        if isinstance(message, int):
            if message == 0:
                return b"\x00"
            length = (message.bit_length() + 7) // 8
            return message.to_bytes(length, "big")
        return str(message).encode("utf-8")

    def encrypt_message(self, message) -> str:
        if not self._sm2 or not self.public_key_hex:
            self.load_public_key()
        plaintext = self._to_bytes(message)
        ciphertext = self._sm2.encrypt(plaintext)
        return base64.b64encode(ciphertext).decode("ascii")

    def decrypt_message(self, ciphertext: str) -> str:
        if not self._sm2 or not self.private_key_hex:
            self.load_private_key_auto()
        raw = base64.b64decode(ciphertext.encode("ascii"))
        plaintext = self._sm2.decrypt(raw)
        try:
            return plaintext.decode("utf-8")
        except UnicodeDecodeError:
            return base64.b64encode(plaintext).decode("ascii")


AsymmetricCryptoService = SM2Service
