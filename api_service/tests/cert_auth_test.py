import argparse
import os
import random
import subprocess
import time
from typing import Optional

import requests
from gmssl import sm2, func

from src.algorithm.ca_center import create_csr, create_root_ca, issue_certificate_from_csr


def resolve_base_url(base_url_arg: str | None) -> str:
    if base_url_arg:
        return base_url_arg

    if "WSL_DISTRO_NAME" in os.environ:
        try:
            result = subprocess.run(
                "ip route | awk '/default/ {print $3}'",
                shell=True,
                capture_output=True,
                text=True,
            )
            gateway_ip = result.stdout.strip()
            if gateway_ip:
                return f"http://{gateway_ip}:8080"
        except Exception:
            pass

    return "http://127.0.0.1:8080"


def create_local_cert_material(username: str, out_dir: str) -> tuple[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    root_priv, root_cert = create_root_ca(common_name="Local Root CA", organization="Secure Ecommerce", country="CN")
    root_cert_path = os.path.join(out_dir, "root_ca.crt.pem")
    with open(root_cert_path, "w", encoding="utf-8") as f:
        f.write(root_cert.to_pem())

    user_priv = func.random_hex(64)
    sm2c = sm2.CryptSM2(public_key="", private_key=user_priv)
    user_pub = sm2c._kg(int(user_priv, 16), sm2c.ecc_table["g"])
    csr = create_csr(username, "Secure Ecommerce", "CN", user_priv, user_pub)
    cert = issue_certificate_from_csr(
        csr=csr,
        issuer_common_name="Local Root CA",
        issuer_organization="Secure Ecommerce",
        issuer_country="CN",
        issuer_private_key_hex=root_priv,
        issuer_public_key_hex=root_cert.subject_public_key_hex,
        is_ca=False,
        years_valid=1,
    )
    cert_path = os.path.join(out_dir, f"{username}.crt.pem")
    key_path = os.path.join(out_dir, f"{username}.private.hex")
    with open(cert_path, "w", encoding="utf-8") as f:
        f.write(cert.to_pem())
    with open(key_path, "w", encoding="utf-8") as f:
        f.write(user_priv)
    return cert_path, key_path


def try_password_login(base_url: str, username: str, password: str, timeout: int) -> Optional[str]:
    r = requests.post(
        f"{base_url}/api/auth/login",
        json={"username": username, "password": password},
        timeout=timeout,
    )
    if r.status_code == 200:
        data = r.json().get("data") or {}
        return data.get("token")
    return None


def ensure_user(base_url: str, username: str, password: str, timeout: int) -> None:
    token = try_password_login(base_url, username, password, timeout)
    if token:
        return
    phone = f"139{random.randint(10000000, 99999999)}"
    email = f"{username}_{int(time.time())}@example.com"
    r = requests.post(
        f"{base_url}/api/users/register",
        json={
            "username": username,
            "password": password,
            "phone": phone,
            "code": "123456",
            "email": email,
        },
        timeout=timeout,
    )
    if r.status_code != 200 or (r.json().get("code") != 0):
        raise RuntimeError(f"注册失败: {r.status_code} {r.text}")
    token = try_password_login(base_url, username, password, timeout)
    if not token:
        raise RuntimeError("注册后密码登录失败")


def cert_login_flow(base_url: str, username: str, cert_pem: str, private_key_hex: str, timeout: int) -> str:
    r1 = requests.post(f"{base_url}/api/auth/cert/challenge", json={"username": username}, timeout=timeout)
    if r1.status_code != 200:
        raise RuntimeError(f"获取挑战失败: {r1.status_code} {r1.text}")
    challenge = (r1.json().get("data") or {}).get("challenge")
    if not challenge:
        raise RuntimeError("挑战字段为空")
    signer = sm2.CryptSM2(public_key="", private_key=private_key_hex)
    signature_hex = signer.sign(challenge.encode("utf-8"), func.random_hex(64))
    r2 = requests.post(
        f"{base_url}/api/auth/cert/login",
        json={
            "username": username,
            "certificate_pem": cert_pem,
            "challenge": challenge,
            "signature_hex": signature_hex,
        },
        timeout=timeout,
    )
    if r2.status_code != 200:
        raise RuntimeError(f"证书登录失败: {r2.status_code} {r2.text}")
    token = ((r2.json().get("data") or {}).get("token"))
    if not token:
        raise RuntimeError(f"证书登录未返回token: {r2.text}")
    return token


def verify_profile(base_url: str, token: str, timeout: int) -> None:
    r = requests.get(
        f"{base_url}/api/users/profile",
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    if r.status_code != 200:
        raise RuntimeError(f"token访问用户信息失败: {r.status_code} {r.text}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--username", default="testuser")
    parser.add_argument("--password", default="TestPass123!")
    parser.add_argument("--out-dir", default=os.path.join("keys", "ca"))
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    base_url = resolve_base_url(args.base_url)

    ensure_user(base_url, args.username, args.password, args.timeout)
    cert_path, key_path = create_local_cert_material(args.username, args.out_dir)
    with open(cert_path, "r", encoding="utf-8") as f:
        cert_pem = f.read()
    with open(key_path, "r", encoding="utf-8") as f:
        private_key_hex = f.read().strip()
    token = cert_login_flow(base_url, args.username, cert_pem, private_key_hex, args.timeout)
    verify_profile(base_url, token, args.timeout)
    print("PASS cert-auth flow")
    print(f"BASE_URL={base_url}")
    print(f"TOKEN_PREFIX={token[:24]}")
    print(f"CERT_PATH={os.path.abspath(cert_path)}")


if __name__ == "__main__":
    main()
