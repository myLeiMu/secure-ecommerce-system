import argparse
import os
import sys


def ensure_project_path():
    current = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    return project_root


def build_fake_cert(username: str, out_dir: str):
    from src.algorithm.ca_center import (
        OID_CLIENT_AUTH,
        create_csr,
        create_root_ca,
        issue_certificate_from_csr,
        parse_certificate_pem,
        sm2_generate_keypair,
    )

    fake_root_private, fake_root_cert = create_root_ca()
    fake_root_info = parse_certificate_pem(fake_root_cert.to_pem())
    user_private, user_public = sm2_generate_keypair()
    user_csr = create_csr(
        subject_common_name=username,
        subject_organization="Secure Ecommerce",
        subject_country="CN",
        subject_private_key_hex=user_private,
        subject_public_key_hex=user_public,
    )
    fake_user_cert = issue_certificate_from_csr(
        user_csr,
        issuer_common_name=fake_root_info.get("subject_common_name") or "Fake Root CA",
        issuer_organization="Fake Org",
        issuer_country="CN",
        issuer_private_key_hex=fake_root_private,
        issuer_public_key_hex=fake_root_info["subject_public_key_hex"],
        is_ca=False,
        years_valid=1,
        eku_oids=[OID_CLIENT_AUTH],
    )
    fake_cert_path = os.path.join(out_dir, f"fake_{username}.crt.pem")
    with open(fake_cert_path, "w", encoding="utf-8") as f:
        f.write(fake_user_cert.to_pem())
    return fake_cert_path


def build_expired_cert(username: str, out_dir: str, project_root: str):
    from src.algorithm.ca_center import (
        OID_CLIENT_AUTH,
        create_csr,
        issue_certificate_from_csr,
        parse_certificate_pem,
        sm2_generate_keypair,
    )
    from src.algorithm.secure_key_storage import SecureKeyStorage

    root_cert_path = os.path.join(project_root, "keys", "ca", "root_ca.crt.pem")
    root_key_secure_path = os.path.join(project_root, "keys", "ca", "root_ca_key_secure.json")
    root_key_password_path = os.path.join(project_root, "keys", "ca", "root_ca_key_password.txt")

    with open(root_cert_path, "r", encoding="utf-8") as f:
        root_cert_pem = f.read()
    root_info = parse_certificate_pem(root_cert_pem)

    with open(root_key_password_path, "r", encoding="utf-8") as f:
        password = f.read().strip()
    root_private = SecureKeyStorage(filepath=root_key_secure_path).decrypt_and_load(password)["private_key"]

    user_private, user_public = sm2_generate_keypair()
    user_csr = create_csr(
        subject_common_name=username,
        subject_organization="Secure Ecommerce",
        subject_country="CN",
        subject_private_key_hex=user_private,
        subject_public_key_hex=user_public,
    )
    expired_user_cert = issue_certificate_from_csr(
        user_csr,
        issuer_common_name=root_info.get("subject_common_name") or "Ecommerce Root CA",
        issuer_organization="Secure Ecommerce",
        issuer_country="CN",
        issuer_private_key_hex=root_private,
        issuer_public_key_hex=root_info["subject_public_key_hex"],
        is_ca=False,
        years_valid=-1,
        eku_oids=[OID_CLIENT_AUTH],
    )
    expired_cert_path = os.path.join(out_dir, f"expired_{username}.crt.pem")
    with open(expired_cert_path, "w", encoding="utf-8") as f:
        f.write(expired_user_cert.to_pem())
    return expired_cert_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default="testuser1")
    parser.add_argument("--out-dir", default=os.path.join("keys", "ca", "demo_bad_certs"))
    args = parser.parse_args()

    project_root = ensure_project_path()
    out_dir = os.path.abspath(os.path.join(project_root, args.out_dir)) if not os.path.isabs(args.out_dir) else os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    fake_cert_path = build_fake_cert(args.username, out_dir)
    expired_cert_path = build_expired_cert(args.username, out_dir, project_root)

    print("PASS generate bad certs")
    print(f"USERNAME={args.username}")
    print(f"FAKE_CERT={fake_cert_path}")
    print(f"EXPIRED_CERT={expired_cert_path}")


if __name__ == "__main__":
    main()
