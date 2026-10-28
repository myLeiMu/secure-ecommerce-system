#!/usr/bin/env python3
"""
PKI系统测试演示
展示改进后的测试输出效果
"""

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


def demo_pki_basic_operations():
    """演示PKI基本操作"""
    print("=" * 60)
    print("PKI系统基本操作演示")
    print("=" * 60)
    
    # 1. 生成根CA
    print("\n[步骤1] 生成根证书颁发机构(CA)...")
    root_priv, root_cert = create_root_ca()
    if verify_certificate_signature(root_cert):
        print("  [SUCCESS] 根CA生成成功")
        print("  - 证书类型: 自签名根证书")
        print("  - 算法: SM2 (国密算法)")
        print("  - 用途: 证书签名、CRL签名")
    else:
        print("  [FAILED] 根CA签名验证失败")
        return False
    
    # 2. 生成用户密钥对和CSR
    print("\n[步骤2] 生成用户密钥对和证书签名请求(CSR)...")
    user_priv, user_pub = sm2_generate_keypair()
    user_csr = create_csr(
        subject_common_name="测试用户",
        subject_organization="安全电商系统",
        subject_country="CN",
        subject_private_key_hex=user_priv,
        subject_public_key_hex=user_pub,
    )
    
    if verify_csr_signature(user_csr):
        print("  [SUCCESS] 用户CSR生成成功")
        print("  - 主体: 测试用户")
        print("  - 组织: 安全电商系统")
        print("  - 密钥对: SM2 (已生成)")
    else:
        print("  [FAILED] 用户CSR签名验证失败")
        return False
    
    # 3. 签发用户证书
    print("\n[步骤3] 使用根CA签发用户证书...")
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
    
    if verify_certificate_signature(user_cert):
        print("  [SUCCESS] 用户证书签发成功")
        print("  - 证书链: 用户证书 → 根CA证书")
        print("  - 有效期: 1年")
        print("  - 扩展用途: 客户端身份验证")
    else:
        print("  [FAILED] 用户证书签名验证失败")
        return False
    
    # 4. 生成服务器证书
    print("\n[步骤4] 生成服务器证书...")
    server_priv, server_pub = sm2_generate_keypair()
    server_csr = create_csr(
        subject_common_name="api.example.com",
        subject_organization="Secure Ecommerce",
        subject_country="CN",
        subject_private_key_hex=server_priv,
        subject_public_key_hex=server_pub,
    )
    
    server_cert = issue_certificate_from_csr(
        server_csr,
        issuer_common_name="Ecommerce Root CA",
        issuer_organization="Secure Ecommerce",
        issuer_country="CN",
        issuer_private_key_hex=root_priv,
        issuer_public_key_hex=root_cert.subject_public_key_hex,
        is_ca=False,
        years_valid=2,
        eku_oids=[OID_SERVER_AUTH],
    )
    
    if verify_certificate_signature(server_cert):
        print("  [SUCCESS] 服务器证书签发成功")
        print("  - 域名: api.example.com")
        print("  - 有效期: 2年")
        print("  - 扩展用途: 服务器身份验证")
    else:
        print("  [FAILED] 服务器证书签名验证失败")
        return False
    
    print("\n" + "=" * 60)
    print("演示完成：所有PKI操作成功执行！")
    print("=" * 60)
    print("总结:")
    print("  [OK] 根CA证书生成与验证")
    print("  [OK] 用户密钥对生成")
    print("  [OK] 证书签名请求(CSR)创建与验证")
    print("  [OK] 用户证书签发与验证")
    print("  [OK] 服务器证书签发与验证")
    print("  [OK] 完整的证书信任链建立")
    
    return True


def demo_certificate_chain():
    """演示证书链验证"""
    print("\n" + "=" * 60)
    print("证书链验证演示")
    print("=" * 60)
    
    # 生成根CA
    print("\n1. 生成根CA...")
    root_priv, root_cert = create_root_ca()
    print("   [OK] 根CA已生成")
    
    # 生成中间CA
    print("\n2. 生成中间CA...")
    intermediate_priv, intermediate_pub = sm2_generate_keypair()
    intermediate_csr = create_csr(
        subject_common_name="Intermediate CA",
        subject_organization="Secure Ecommerce",
        subject_country="CN",
        subject_private_key_hex=intermediate_priv,
        subject_public_key_hex=intermediate_pub,
    )
    
    intermediate_cert = issue_certificate_from_csr(
        intermediate_csr,
        issuer_common_name="Ecommerce Root CA",
        issuer_organization="Secure Ecommerce",
        issuer_country="CN",
        issuer_private_key_hex=root_priv,
        issuer_public_key_hex=root_cert.subject_public_key_hex,
        is_ca=True,
        years_valid=5,
    )
    
    if verify_certificate_signature(intermediate_cert):
        print("   [OK] 中间CA证书签发成功")
    else:
        print("   [ERROR] 中间CA证书验证失败")
        return False
    
    # 生成最终用户证书
    print("\n3. 生成最终用户证书...")
    user_priv, user_pub = sm2_generate_keypair()
    user_csr = create_csr(
        subject_common_name="最终用户",
        subject_organization="安全电商",
        subject_country="CN",
        subject_private_key_hex=user_priv,
        subject_public_key_hex=user_pub,
    )
    
    user_cert = issue_certificate_from_csr(
        user_csr,
        issuer_common_name="Intermediate CA",
        issuer_organization="Secure Ecommerce",
        issuer_country="CN",
        issuer_private_key_hex=intermediate_priv,
        issuer_public_key_hex=intermediate_cert.subject_public_key_hex,
        is_ca=False,
        years_valid=1,
        eku_oids=[OID_CLIENT_AUTH],
    )
    
    if verify_certificate_signature(user_cert):
        print("   [OK] 最终用户证书签发成功")
    else:
        print("   [ERROR] 最终用户证书验证失败")
        return False
    
    print("\n证书链结构:")
    print("  ┌─────────────────┐")
    print("  │  根CA证书       │")
    print("  │  (自签名)       │")
    print("  └────────┬────────┘")
    print("           ↓ 签名")
    print("  ┌─────────────────┐")
    print("  │  中间CA证书     │")
    print("  └────────┬────────┘")
    print("           ↓ 签名")
    print("  ┌─────────────────┐")
    print("  │  最终用户证书   │")
    print("  └─────────────────┘")
    
    print("\n[SUCCESS] 完整的证书链验证演示完成！")
    return True


def main():
    """主函数"""
    print("PKI系统测试演示程序")
    print("版本: 1.0")
    print("日期: 2026-06-29")
    print()
    
    # 演示基本操作
    if not demo_pki_basic_operations():
        print("\n[ERROR] PKI基本操作演示失败")
        return 1
    
    # 演示证书链
    if not demo_certificate_chain():
        print("\n[ERROR] 证书链验证演示失败")
        return 1
    
    print("\n" + "=" * 60)
    print("所有演示成功完成！")
    print("=" * 60)
    print("\n测试输出改进效果:")
    print("  - 清晰的步骤指示 ([步骤1], [步骤2]...)")
    print("  - 明确的结果标记 ([SUCCESS], [FAILED])")
    print("  - 详细的操作信息")
    print("  - 可视化的证书链结构")
    print("  - 完整的测试总结")
    
    return 0


if __name__ == "__main__":
    exit(main())