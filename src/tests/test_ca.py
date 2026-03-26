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
    root_priv, root_cert = create_root_ca()
    assert verify_certificate_signature(root_cert)

    merchant_priv, merchant_pub = sm2_generate_keypair()
    merchant_csr = create_csr(
        subject_common_name="Merchant",
        subject_organization="Secure Ecommerce",
        subject_country="CN",
        subject_private_key_hex=merchant_priv,
        subject_public_key_hex=merchant_pub,
    )
    assert verify_csr_signature(merchant_csr)

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

    user_priv, user_pub = sm2_generate_keypair()
    user_csr = create_csr(
        subject_common_name="User",
        subject_organization="Secure Ecommerce",
        subject_country="CN",
        subject_private_key_hex=user_priv,
        subject_public_key_hex=user_pub,
    )
    assert verify_csr_signature(user_csr)

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


if __name__ == "__main__":
    test_ca_issue_and_verify()
