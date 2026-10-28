from src.algorithm.ca_center import (
    OID_CLIENT_AUTH,
    OID_SERVER_AUTH,
    create_csr,
    create_root_ca,
    issue_certificate_from_csr,
    sm2_generate_keypair,
    verify_certificate_signature,
    verify_csr_signature,
)


def test_ca_issue_and_verify():
    print("=" * 60)
    print("开始测试：CA证书签发与验证流程")
    print("=" * 60)
    
    # 1. 测试根CA生成
    print("\n[1/5] 测试根CA生成...")
    root_priv, root_cert = create_root_ca()
    assert verify_certificate_signature(root_cert)
    print("[PASS] 根CA生成成功，自签名验证通过")
    print(f"  根CA类型: 自签名证书")
    print(f"  密钥长度: SM2 (256位)")
    
    # 2. 测试商户CSR生成
    print("\n[2/5] 测试商户CSR生成...")
    merchant_priv, merchant_pub = sm2_generate_keypair()
    merchant_csr = create_csr(
        subject_common_name="Merchant",
        subject_organization="Secure Ecommerce",
        subject_country="CN",
        subject_private_key_hex=merchant_priv,
        subject_public_key_hex=merchant_pub,
    )
    assert verify_csr_signature(merchant_csr)
    print("[PASS] 商户CSR生成成功，签名验证通过")
    print(f"  CSR主体: Merchant (商户)")
    
    # 3. 测试商户证书签发
    print("\n[3/5] 测试商户证书签发...")
    merchant_cert = issue_certificate_from_csr(
        merchant_csr,
        issuer_common_name="Ecommerce Root CA",
        issuer_organization="Secure Ecommerce",
        issuer_country="CN",
        issuer_private_key_hex=root_priv,
        issuer_public_key_hex=root_cert.subject_public_key_hex,
        is_ca=False,
        years_valid=2,
        eku_oids=[OID_SERVER_AUTH],
    )
    assert verify_certificate_signature(merchant_cert)
    print("[PASS] 商户证书签发成功，签名验证通过")
    print(f"  证书类型: 服务器身份验证")
    print(f"  扩展密钥用法: 服务器认证")
    
    # 4. 测试用户CSR生成
    print("\n[4/5] 测试用户CSR生成...")
    user_priv, user_pub = sm2_generate_keypair()
    user_csr = create_csr(
        subject_common_name="User",
        subject_organization="Secure Ecommerce",
        subject_country="CN",
        subject_private_key_hex=user_priv,
        subject_public_key_hex=user_pub,
    )
    assert verify_csr_signature(user_csr)
    print("[PASS] 用户CSR生成成功，签名验证通过")
    print(f"  CSR主体: User (用户)")
    
    # 5. 测试用户证书签发
    print("\n[5/5] 测试用户证书签发...")
    user_cert = issue_certificate_from_csr(
        user_csr,
        issuer_common_name="Ecommerce Root CA",
        issuer_organization="Secure Ecommerce",
        issuer_country="CN",
        issuer_private_key_hex=root_priv,
        issuer_public_key_hex=root_cert.subject_public_key_hex,
        is_ca=False,
        years_valid=1,
        eku_oids=[OID_CLIENT_AUTH],
    )
    assert verify_certificate_signature(user_cert)
    print("[PASS] 用户证书签发成功，签名验证通过")
    print(f"  证书类型: 客户端身份验证")
    print(f"  扩展密钥用法: 客户端认证")
    
    print("\n" + "=" * 60)
    print("测试完成：所有5个测试用例全部通过！")
    print("=" * 60)


if __name__ == "__main__":
    test_ca_issue_and_verify()
