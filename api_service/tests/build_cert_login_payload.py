import argparse
import json
import os
import subprocess

import requests
from gmssl import sm2, func


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--username", default="testuser")
    parser.add_argument("--cert-path", default=os.path.join("keys", "ca", "testuser.crt.pem"))
    parser.add_argument("--key-path", default=os.path.join("keys", "ca", "testuser.private.hex"))
    parser.add_argument("--out-file", default=os.path.join("api_service", "tests", "cert_login_payload.json"))
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--execute-login", action="store_true")
    args = parser.parse_args()

    base_url = resolve_base_url(args.base_url)

    with open(args.cert_path, "r", encoding="utf-8") as f:
        certificate_pem = f.read()
    with open(args.key_path, "r", encoding="utf-8") as f:
        private_key_hex = f.read().strip()

    challenge_resp = requests.post(
        f"{base_url}/api/auth/cert/challenge",
        json={"username": args.username},
        timeout=args.timeout,
    )
    if challenge_resp.status_code != 200:
        raise RuntimeError(f"challenge失败: {challenge_resp.status_code} {challenge_resp.text}")
    challenge = (challenge_resp.json().get("data") or {}).get("challenge")
    if not challenge:
        raise RuntimeError("challenge为空")

    signer = sm2.CryptSM2(public_key="", private_key=private_key_hex)
    signature_hex = signer.sign(challenge.encode("utf-8"), func.random_hex(64))

    payload = {
        "username": args.username,
        "certificate_pem": certificate_pem,
        "challenge": challenge,
        "signature_hex": signature_hex,
    }

    out_path = os.path.abspath(args.out_file)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"PASS payload generated")
    print(f"BASE_URL={base_url}")
    print(f"PAYLOAD_FILE={out_path}")

    if args.execute_login:
        login_resp = requests.post(
            f"{base_url}/api/auth/cert/login",
            json=payload,
            timeout=args.timeout,
        )
        print(f"LOGIN_STATUS={login_resp.status_code}")
        print(login_resp.text)


if __name__ == "__main__":
    main()
