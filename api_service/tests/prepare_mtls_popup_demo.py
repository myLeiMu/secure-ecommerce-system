import argparse
import os
import subprocess


def run(command: str, env: dict | None = None):
    result = subprocess.run(command, shell=True, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"{command}\n{result.stderr.strip()}")


def to_posix(path: str) -> str:
    return os.path.abspath(path).replace("\\", "/")


def build_openssl_env(out_dir: str) -> dict:
    env = os.environ.copy()
    if env.get("OPENSSL_CONF") and os.path.exists(env["OPENSSL_CONF"]):
        return env

    common_candidates = [
        r"C:\Program Files\OpenSSL-Win64\bin\openssl.cfg",
        r"C:\Program Files\OpenSSL-Win32\bin\openssl.cfg",
        r"C:\OpenSSL-Win64\bin\openssl.cfg",
        r"C:\OpenSSL-Win32\bin\openssl.cfg",
    ]
    for candidate in common_candidates:
        if os.path.exists(candidate):
            env["OPENSSL_CONF"] = candidate
            return env

    local_conf = os.path.join(out_dir, "openssl_local.cnf")
    with open(local_conf, "w", encoding="utf-8") as f:
        f.write(
            "[req]\n"
            "distinguished_name = req_distinguished_name\n"
            "[req_distinguished_name]\n"
        )
    env["OPENSSL_CONF"] = local_conf
    return env


def resolve_backend_url(backend_url_arg: str | None) -> str:
    if backend_url_arg:
        return backend_url_arg

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
    parser.add_argument("--out-dir", default=os.path.join("keys", "mtls_demo"))
    parser.add_argument("--p12-password", default="123456")
    parser.add_argument("--backend-url", default=None)
    args = parser.parse_args()
    backend_url = resolve_backend_url(args.backend_url)

    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    ca_key = os.path.join(out_dir, "demo_ca.key")
    ca_crt = os.path.join(out_dir, "demo_ca.crt")
    server_key = os.path.join(out_dir, "server.key")
    server_csr = os.path.join(out_dir, "server.csr")
    server_crt = os.path.join(out_dir, "server.crt")
    client_key = os.path.join(out_dir, "client_testuser.key")
    client_csr = os.path.join(out_dir, "client_testuser.csr")
    client_crt = os.path.join(out_dir, "client_testuser.crt")
    client_p12 = os.path.join(out_dir, "client_testuser.p12")
    nginx_conf = os.path.join(out_dir, "nginx_mtls_demo.conf")
    openssl_env = build_openssl_env(out_dir)

    run(f'openssl req -x509 -newkey rsa:2048 -nodes -keyout "{ca_key}" -out "{ca_crt}" -days 3650 -subj "/CN=Demo Root CA"', openssl_env)
    run(f'openssl req -new -newkey rsa:2048 -nodes -keyout "{server_key}" -out "{server_csr}" -subj "/CN=localhost"', openssl_env)
    run(f'openssl x509 -req -in "{server_csr}" -CA "{ca_crt}" -CAkey "{ca_key}" -CAcreateserial -out "{server_crt}" -days 825 -sha256', openssl_env)
    run(f'openssl req -new -newkey rsa:2048 -nodes -keyout "{client_key}" -out "{client_csr}" -subj "/CN=testuser"', openssl_env)
    run(f'openssl x509 -req -in "{client_csr}" -CA "{ca_crt}" -CAkey "{ca_key}" -CAcreateserial -out "{client_crt}" -days 825 -sha256', openssl_env)
    run(f'openssl pkcs12 -export -out "{client_p12}" -inkey "{client_key}" -in "{client_crt}" -certfile "{ca_crt}" -passout pass:{args.p12_password}', openssl_env)

    conf_text = (
        "server {\n"
        "    listen 8443 ssl;\n"
        "    server_name localhost;\n"
        f"    ssl_certificate     {to_posix(server_crt)};\n"
        f"    ssl_certificate_key {to_posix(server_key)};\n"
        f"    ssl_client_certificate {to_posix(ca_crt)};\n"
        "    ssl_verify_client on;\n"
        "    ssl_verify_depth 2;\n"
        "    location /api/ {\n"
        f"        proxy_pass {backend_url};\n"
        "        proxy_set_header Host $host;\n"
        "        proxy_set_header X-Real-IP $remote_addr;\n"
        "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
        "        proxy_set_header X-Forwarded-Proto $scheme;\n"
        "        proxy_set_header X-Forwarded-Host $host;\n"
        "        proxy_set_header X-Forwarded-Port $server_port;\n"
        "        proxy_set_header X-SSL-CLIENT-VERIFY $ssl_client_verify;\n"
        "        proxy_set_header X-SSL-CLIENT-CERT $ssl_client_escaped_cert;\n"
        "        proxy_set_header X-SSL-CLIENT-S-DN $ssl_client_s_dn;\n"
        "    }\n"
        "    location /static/ {\n"
        f"        proxy_pass {backend_url};\n"
        "        proxy_set_header Host $host;\n"
        "        proxy_set_header X-Real-IP $remote_addr;\n"
        "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
        "        proxy_set_header X-Forwarded-Proto $scheme;\n"
        "        proxy_set_header X-Forwarded-Host $host;\n"
        "        proxy_set_header X-Forwarded-Port $server_port;\n"
        "    }\n"
        "}\n"
    )
    with open(nginx_conf, "w", encoding="utf-8") as f:
        f.write(conf_text)

    print("PASS prepare mtls popup demo")
    print(f"P12_FILE={client_p12}")
    print(f"P12_PASSWORD={args.p12_password}")
    print(f"Nginx_CONF={nginx_conf}")
    print(f"BACKEND_URL={backend_url}")
    print(f"OPENSSL_CONF={openssl_env.get('OPENSSL_CONF', '')}")
    # print("NEXT_1=导入P12到浏览器证书管理（当前用户-个人）")
    # print("NEXT_2=启动后端: conda activate WAF && python api_service\\manage.py runserver 0.0.0.0:8080")
    # print(f"NEXT_3=用nginx -c {nginx_conf} 启动mTLS代理")
    # print("NEXT_4=访问 https://localhost:8443/api/health/ 查看证书弹窗")
    # print("NEXT_5=POST https://localhost:8443/api/auth/cert/mtls-login body:{\"username\":\"testuser\"}")


if __name__ == "__main__":
    main()
