import base64
import datetime
import os
import secrets
from dataclasses import dataclass
from typing import Iterable, Optional

from gmssl import func, sm2

from src.utils.security import sm3_digest
from src.algorithm.secure_key_storage import SecureKeyStorage


def _der_len(length: int) -> bytes:
    if length < 0:
        raise ValueError("negative length")
    if length < 0x80:
        return bytes([length])
    out = []
    n = length
    while n:
        out.append(n & 0xFF)
        n >>= 8
    out.reverse()
    return bytes([0x80 | len(out)]) + bytes(out)


def _der(tag: int, content: bytes) -> bytes:
    return bytes([tag]) + _der_len(len(content)) + content


def der_sequence(items: Iterable[bytes]) -> bytes:
    return _der(0x30, b"".join(items))


def der_set(items: Iterable[bytes]) -> bytes:
    return _der(0x31, b"".join(items))


def der_integer(value: int) -> bytes:
    if value < 0:
        raise ValueError("only non-negative integers supported")
    if value == 0:
        encoded = b"\x00"
    else:
        encoded = value.to_bytes((value.bit_length() + 7) // 8, "big")
        if encoded[0] & 0x80:
            encoded = b"\x00" + encoded
    return _der(0x02, encoded)


def der_boolean(value: bool) -> bytes:
    return _der(0x01, b"\xFF" if value else b"\x00")


def der_octet_string(data: bytes) -> bytes:
    return _der(0x04, data)


def der_bit_string(data: bytes, unused_bits: int = 0) -> bytes:
    if not (0 <= unused_bits <= 7):
        raise ValueError("invalid unused_bits")
    return _der(0x03, bytes([unused_bits]) + data)


def der_utf8_string(text: str) -> bytes:
    return _der(0x0C, text.encode("utf-8"))


def der_printable_string(text: str) -> bytes:
    return _der(0x13, text.encode("ascii"))


def der_utctime(dt: datetime.datetime) -> bytes:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    dt = dt.astimezone(datetime.timezone.utc)
    return _der(0x17, dt.strftime("%y%m%d%H%M%SZ").encode("ascii"))


def der_oid(oid: str) -> bytes:
    parts = [int(x) for x in oid.split(".")]
    if len(parts) < 2:
        raise ValueError("invalid oid")
    if parts[0] > 2 or parts[1] > 39:
        raise ValueError("invalid oid first arcs")
    out = bytearray()
    out.append(40 * parts[0] + parts[1])
    for arc in parts[2:]:
        if arc < 0:
            raise ValueError("invalid oid arc")
        stack = [arc & 0x7F]
        arc >>= 7
        while arc:
            stack.append(0x80 | (arc & 0x7F))
            arc >>= 7
        out.extend(reversed(stack))
    return _der(0x06, bytes(out))


def _pem_block(label: str, der_bytes: bytes) -> str:
    b64 = base64.b64encode(der_bytes).decode("ascii")
    lines = [b64[i : i + 64] for i in range(0, len(b64), 64)]
    body = "\n".join(lines)
    return f"-----BEGIN {label}-----\n{body}\n-----END {label}-----\n"


OID_ID_EC_PUBLIC_KEY = "1.2.840.10045.2.1"
OID_SM2P256V1 = "1.2.156.10197.1.301"
OID_SM2_WITH_SM3 = "1.2.156.10197.1.501"

OID_CN = "2.5.4.3"
OID_O = "2.5.4.10"
OID_OU = "2.5.4.11"
OID_C = "2.5.4.6"

OID_BASIC_CONSTRAINTS = "2.5.29.19"
OID_KEY_USAGE = "2.5.29.15"
OID_SUBJECT_KEY_IDENTIFIER = "2.5.29.14"
OID_AUTHORITY_KEY_IDENTIFIER = "2.5.29.35"
OID_EXTENDED_KEY_USAGE = "2.5.29.37"

OID_SERVER_AUTH = "1.3.6.1.5.5.7.3.1"
OID_CLIENT_AUTH = "1.3.6.1.5.5.7.3.2"


def sm2_generate_keypair() -> tuple[str, str]:
    private_key_hex = func.random_hex(64)
    crypt = sm2.CryptSM2(public_key="", private_key=private_key_hex)
    public_key_hex = crypt._kg(int(private_key_hex, 16), crypt.ecc_table["g"])
    return private_key_hex, public_key_hex


def sm2_public_key_bitstring(public_key_hex: str) -> bytes:
    raw = bytes.fromhex("04" + public_key_hex)
    return der_bit_string(raw, unused_bits=0)


def algorithm_identifier_sm2_with_sm3() -> bytes:
    return der_sequence([der_oid(OID_SM2_WITH_SM3)])


def algorithm_identifier_ec_sm2() -> bytes:
    return der_sequence([der_oid(OID_ID_EC_PUBLIC_KEY), der_oid(OID_SM2P256V1)])


def encode_name(common_name: str, organization: Optional[str] = None, org_unit: Optional[str] = None, country: str = "CN") -> bytes:
    rdns = []
    if country:
        rdns.append(der_set([der_sequence([der_oid(OID_C), der_printable_string(country)])]))
    if organization:
        rdns.append(der_set([der_sequence([der_oid(OID_O), der_utf8_string(organization)])]))
    if org_unit:
        rdns.append(der_set([der_sequence([der_oid(OID_OU), der_utf8_string(org_unit)])]))
    rdns.append(der_set([der_sequence([der_oid(OID_CN), der_utf8_string(common_name)])]))
    return der_sequence(rdns)


def _key_usage_bitstring(usages: set[str]) -> bytes:
    mapping = {
        "digitalSignature": 0,
        "nonRepudiation": 1,
        "keyEncipherment": 2,
        "dataEncipherment": 3,
        "keyAgreement": 4,
        "keyCertSign": 5,
        "cRLSign": 6,
        "encipherOnly": 7,
        "decipherOnly": 8,
    }
    bits = [mapping[u] for u in usages]
    nbits = max(bits) + 1 if bits else 0
    nbytes = (nbits + 7) // 8 if nbits else 1
    buf = bytearray(b"\x00" * nbytes)
    for b in bits:
        idx = b // 8
        off = b % 8
        buf[idx] |= 1 << (7 - off)
    unused = (8 - (nbits % 8)) % 8 if nbits else 7
    return der_bit_string(bytes(buf), unused_bits=unused)


def _extension(oid: str, value_der: bytes, critical: bool = False) -> bytes:
    items = [der_oid(oid)]
    if critical:
        items.append(der_boolean(True))
    items.append(der_octet_string(value_der))
    return der_sequence(items)


def _ext_basic_constraints(ca: bool, path_len: Optional[int] = None, critical: bool = True) -> bytes:
    inner = [der_boolean(ca)]
    if path_len is not None:
        inner.append(der_integer(path_len))
    value = der_sequence(inner)
    return _extension(OID_BASIC_CONSTRAINTS, value, critical=critical)


def _ext_key_usage(usages: set[str], critical: bool = True) -> bytes:
    value = _key_usage_bitstring(usages)
    return _extension(OID_KEY_USAGE, value, critical=critical)


def _ext_subject_key_identifier(key_id: bytes) -> bytes:
    value = der_octet_string(key_id)
    return _extension(OID_SUBJECT_KEY_IDENTIFIER, value, critical=False)


def _ext_authority_key_identifier(key_id: bytes) -> bytes:
    key_id_tagged = _der(0x80, key_id)
    value = der_sequence([key_id_tagged])
    return _extension(OID_AUTHORITY_KEY_IDENTIFIER, value, critical=False)


def _ext_extended_key_usage(oids: list[str]) -> bytes:
    value = der_sequence([der_oid(x) for x in oids])
    return _extension(OID_EXTENDED_KEY_USAGE, value, critical=False)


def _ecdsa_like_sig_der_from_raw(raw_sig: bytes) -> bytes:
    if len(raw_sig) != 64:
        raise ValueError("invalid sm2 signature length")
    r = int.from_bytes(raw_sig[:32], "big")
    s = int.from_bytes(raw_sig[32:], "big")
    return der_sequence([der_integer(r), der_integer(s)])


def _raw_sig_from_ecdsa_like_der(sig_der: bytes) -> bytes:
    if not sig_der or sig_der[0] != 0x30:
        raise ValueError("invalid signature der")
    pos = 1
    length_byte = sig_der[pos]
    pos += 1
    if length_byte & 0x80:
        n = length_byte & 0x7F
        length = int.from_bytes(sig_der[pos : pos + n], "big")
        pos += n
    else:
        length = length_byte
    end = pos + length
    if end != len(sig_der):
        raise ValueError("invalid signature der length")

    def read_integer(p: int) -> tuple[int, int]:
        if sig_der[p] != 0x02:
            raise ValueError("invalid integer")
        p += 1
        lb = sig_der[p]
        p += 1
        if lb & 0x80:
            n2 = lb & 0x7F
            ln = int.from_bytes(sig_der[p : p + n2], "big")
            p += n2
        else:
            ln = lb
        v = int.from_bytes(sig_der[p : p + ln], "big", signed=False)
        return v, p + ln

    r, pos = read_integer(pos)
    s, pos = read_integer(pos)
    if pos != end:
        raise ValueError("trailing data")
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


@dataclass(frozen=True)
class X509Certificate:
    der: bytes
    tbs_der: bytes
    signature_der: bytes
    subject_public_key_hex: str
    issuer_public_key_hex: str

    def to_pem(self) -> str:
        return _pem_block("CERTIFICATE", self.der)


@dataclass(frozen=True)
class X509CSR:
    der: bytes
    info_der: bytes
    signature_der: bytes
    subject_public_key_hex: str

    def to_pem(self) -> str:
        return _pem_block("CERTIFICATE REQUEST", self.der)


def create_root_ca(
    common_name: str = "Ecommerce Root CA",
    organization: str = "Secure Ecommerce",
    country: str = "CN",
    years_valid: int = 10,
) -> tuple[str, X509Certificate]:
    root_priv, root_pub = sm2_generate_keypair()
    issuer = encode_name(common_name, organization=organization, country=country)
    subject = issuer

    now = datetime.datetime.now(datetime.timezone.utc)
    not_before = now - datetime.timedelta(minutes=5)
    not_after = now + datetime.timedelta(days=365 * years_valid)

    spki = der_sequence([algorithm_identifier_ec_sm2(), sm2_public_key_bitstring(root_pub)])
    key_id = sm3_digest(bytes.fromhex("04" + root_pub))

    extensions = [
        _ext_basic_constraints(ca=True, path_len=1, critical=True),
        _ext_key_usage({"keyCertSign", "cRLSign"}, critical=True),
        _ext_subject_key_identifier(key_id),
        _ext_authority_key_identifier(key_id),
    ]
    ext_seq = der_sequence(extensions)
    extensions_explicit = _der(0xA3, ext_seq)

    serial = int.from_bytes(secrets.token_bytes(16), "big") or 1
    tbs_items = [
        _der(0xA0, der_integer(2)),
        der_integer(serial),
        algorithm_identifier_sm2_with_sm3(),
        issuer,
        der_sequence([der_utctime(not_before), der_utctime(not_after)]),
        subject,
        spki,
        extensions_explicit,
    ]
    tbs_der = der_sequence(tbs_items)

    signer = sm2.CryptSM2(public_key=root_pub, private_key=root_priv)
    sig_raw_hex = signer.sign(tbs_der, func.random_hex(64))
    sig_der = _ecdsa_like_sig_der_from_raw(bytes.fromhex(sig_raw_hex))

    cert_der = der_sequence([tbs_der, algorithm_identifier_sm2_with_sm3(), der_bit_string(sig_der, 0)])
    cert = X509Certificate(
        der=cert_der,
        tbs_der=tbs_der,
        signature_der=sig_der,
        subject_public_key_hex=root_pub,
        issuer_public_key_hex=root_pub,
    )
    return root_priv, cert


def create_csr(
    subject_common_name: str,
    subject_organization: str,
    subject_country: str,
    subject_private_key_hex: str,
    subject_public_key_hex: str,
) -> X509CSR:
    subject = encode_name(subject_common_name, organization=subject_organization, country=subject_country)
    spki = der_sequence([algorithm_identifier_ec_sm2(), sm2_public_key_bitstring(subject_public_key_hex)])
    version = der_integer(0)
    attrs = _der(0xA0, b"")
    info_der = der_sequence([version, subject, spki, attrs])

    signer = sm2.CryptSM2(public_key=subject_public_key_hex, private_key=subject_private_key_hex)
    sig_raw_hex = signer.sign(info_der, func.random_hex(64))
    sig_der = _ecdsa_like_sig_der_from_raw(bytes.fromhex(sig_raw_hex))

    csr_der = der_sequence([info_der, algorithm_identifier_sm2_with_sm3(), der_bit_string(sig_der, 0)])
    return X509CSR(
        der=csr_der,
        info_der=info_der,
        signature_der=sig_der,
        subject_public_key_hex=subject_public_key_hex,
    )


def issue_certificate_from_csr(
    csr: X509CSR,
    issuer_common_name: str,
    issuer_organization: str,
    issuer_country: str,
    issuer_private_key_hex: str,
    issuer_public_key_hex: str,
    is_ca: bool,
    years_valid: int,
    eku_oids: Optional[list[str]] = None,
) -> X509Certificate:
    issuer = encode_name(issuer_common_name, organization=issuer_organization, country=issuer_country)

    now = datetime.datetime.now(datetime.timezone.utc)
    not_before = now - datetime.timedelta(minutes=5)
    not_after = now + datetime.timedelta(days=365 * years_valid)

    key_id = sm3_digest(bytes.fromhex("04" + csr.subject_public_key_hex))
    issuer_key_id = sm3_digest(bytes.fromhex("04" + issuer_public_key_hex))

    extensions = []
    if is_ca:
        extensions.append(_ext_basic_constraints(ca=True, path_len=0, critical=True))
        extensions.append(_ext_key_usage({"keyCertSign", "cRLSign"}, critical=True))
    else:
        extensions.append(_ext_key_usage({"digitalSignature"}, critical=True))
        if eku_oids:
            extensions.append(_ext_extended_key_usage(eku_oids))
    extensions.append(_ext_subject_key_identifier(key_id))
    extensions.append(_ext_authority_key_identifier(issuer_key_id))

    ext_seq = der_sequence(extensions)
    extensions_explicit = _der(0xA3, ext_seq)

    serial = int.from_bytes(secrets.token_bytes(16), "big") or 1

    subject = _extract_subject_from_csr_info(csr.info_der)
    spki = _extract_spki_from_csr_info(csr.info_der)

    tbs_der = der_sequence(
        [
            _der(0xA0, der_integer(2)),
            der_integer(serial),
            algorithm_identifier_sm2_with_sm3(),
            issuer,
            der_sequence([der_utctime(not_before), der_utctime(not_after)]),
            subject,
            spki,
            extensions_explicit,
        ]
    )

    signer = sm2.CryptSM2(public_key=issuer_public_key_hex, private_key=issuer_private_key_hex)
    sig_raw_hex = signer.sign(tbs_der, func.random_hex(64))
    sig_der = _ecdsa_like_sig_der_from_raw(bytes.fromhex(sig_raw_hex))

    cert_der = der_sequence([tbs_der, algorithm_identifier_sm2_with_sm3(), der_bit_string(sig_der, 0)])
    return X509Certificate(
        der=cert_der,
        tbs_der=tbs_der,
        signature_der=sig_der,
        subject_public_key_hex=csr.subject_public_key_hex,
        issuer_public_key_hex=issuer_public_key_hex,
    )


def verify_certificate_signature(cert: X509Certificate) -> bool:
    verifier = sm2.CryptSM2(public_key=cert.issuer_public_key_hex, private_key="")
    raw = _raw_sig_from_ecdsa_like_der(cert.signature_der)
    sig_hex = raw.hex()
    return bool(verifier.verify(sig_hex, cert.tbs_der))


def verify_csr_signature(csr: X509CSR) -> bool:
    verifier = sm2.CryptSM2(public_key=csr.subject_public_key_hex, private_key="")
    raw = _raw_sig_from_ecdsa_like_der(csr.signature_der)
    sig_hex = raw.hex()
    return bool(verifier.verify(sig_hex, csr.info_der))


def parse_certificate_pem(cert_pem: str) -> dict:
    cert_der = _pem_to_der(cert_pem, "CERTIFICATE")
    cert_children = _decode_top_sequence_children(cert_der)
    if len(cert_children) != 3:
        raise ValueError("invalid certificate structure")
    tbs_der = cert_children[0]
    tbs_children = _decode_top_sequence_children(tbs_der)
    if len(tbs_children) < 7:
        raise ValueError("invalid tbs certificate structure")
    issuer_name_der = tbs_children[3]
    subject_name_der = tbs_children[5]
    spki_der = tbs_children[6]
    subject_common_name = _extract_common_name_from_name_der(subject_name_der)
    subject_public_key_hex = _extract_subject_public_key_hex_from_spki(spki_der)
    _, sig_content_start, sig_content_end, _ = _read_tlv(cert_children[2], 0)
    sig_content = cert_children[2][sig_content_start:sig_content_end]
    if not sig_content:
        raise ValueError("invalid signature bit string")
    signature_der = sig_content[1:]
    return {
        "der": cert_der,
        "tbs_der": tbs_der,
        "signature_der": signature_der,
        "issuer_name_der": issuer_name_der,
        "subject_name_der": subject_name_der,
        "subject_common_name": subject_common_name,
        "subject_public_key_hex": subject_public_key_hex,
    }


def verify_certificate_with_root(cert_pem: str, root_cert_pem: str) -> bool:
    cert_info = parse_certificate_pem(cert_pem)
    root_info = parse_certificate_pem(root_cert_pem)
    if cert_info["issuer_name_der"] != root_info["subject_name_der"]:
        return False
    verifier = sm2.CryptSM2(public_key=root_info["subject_public_key_hex"], private_key="")
    raw = _raw_sig_from_ecdsa_like_der(cert_info["signature_der"])
    return bool(verifier.verify(raw.hex(), cert_info["tbs_der"]))


def _extract_subject_from_csr_info(info_der: bytes) -> bytes:
    elements = _decode_top_sequence_children(info_der)
    if len(elements) < 4:
        raise ValueError("invalid csr info")
    return elements[1]


def _extract_spki_from_csr_info(info_der: bytes) -> bytes:
    elements = _decode_top_sequence_children(info_der)
    if len(elements) < 4:
        raise ValueError("invalid csr info")
    return elements[2]


def _decode_top_sequence_children(der_bytes: bytes) -> list[bytes]:
    if not der_bytes or der_bytes[0] != 0x30:
        raise ValueError("expected sequence")
    pos = 1
    length_byte = der_bytes[pos]
    pos += 1
    if length_byte & 0x80:
        n = length_byte & 0x7F
        length = int.from_bytes(der_bytes[pos : pos + n], "big")
        pos += n
    else:
        length = length_byte
    end = pos + length
    if end != len(der_bytes):
        raise ValueError("invalid sequence length")
    children = []
    while pos < end:
        start = pos
        pos += 1
        lb = der_bytes[pos]
        pos += 1
        if lb & 0x80:
            n2 = lb & 0x7F
            ln = int.from_bytes(der_bytes[pos : pos + n2], "big")
            pos += n2
        else:
            ln = lb
        pos += ln
        children.append(der_bytes[start:pos])
    return children


def _read_tlv(data: bytes, offset: int) -> tuple[int, int, int, int]:
    if offset >= len(data):
        raise ValueError("invalid tlv offset")
    tag = data[offset]
    pos = offset + 1
    if pos >= len(data):
        raise ValueError("invalid tlv length")
    lb = data[pos]
    pos += 1
    if lb & 0x80:
        n = lb & 0x7F
        if pos + n > len(data):
            raise ValueError("invalid tlv length bytes")
        ln = int.from_bytes(data[pos:pos + n], "big")
        pos += n
    else:
        ln = lb
    content_start = pos
    content_end = pos + ln
    if content_end > len(data):
        raise ValueError("invalid tlv content length")
    return tag, content_start, content_end, content_end


def _extract_subject_public_key_hex_from_spki(spki_der: bytes) -> str:
    children = _decode_top_sequence_children(spki_der)
    if len(children) != 2:
        raise ValueError("invalid spki")
    _, content_start, content_end, _ = _read_tlv(children[1], 0)
    bit_str = children[1][content_start:content_end]
    if len(bit_str) < 2:
        raise ValueError("invalid spki bit string")
    raw_key = bit_str[1:]
    if raw_key[0] == 0x04:
        raw_key = raw_key[1:]
    return raw_key.hex()


def _extract_common_name_from_name_der(name_der: bytes) -> str:
    rdn_sets = _decode_top_sequence_children(name_der)
    for rdn_set in rdn_sets:
        _, set_content_start, set_content_end, _ = _read_tlv(rdn_set, 0)
        set_content = rdn_set[set_content_start:set_content_end]
        attrs = _decode_top_sequence_children(_der(0x30, set_content))
        for attr in attrs:
            seq_children = _decode_top_sequence_children(attr)
            if len(seq_children) < 2:
                continue
            oid = _decode_oid_tlv(seq_children[0])
            if oid == OID_CN:
                _, v_start, v_end, _ = _read_tlv(seq_children[1], 0)
                return seq_children[1][v_start:v_end].decode("utf-8", errors="ignore")
    return ""


def _decode_oid_tlv(oid_tlv: bytes) -> str:
    if not oid_tlv or oid_tlv[0] != 0x06:
        raise ValueError("invalid oid tlv")
    _, start, end, _ = _read_tlv(oid_tlv, 0)
    data = oid_tlv[start:end]
    if not data:
        raise ValueError("empty oid")
    first = data[0]
    arcs = [first // 40, first % 40]
    value = 0
    for b in data[1:]:
        value = (value << 7) | (b & 0x7F)
        if not (b & 0x80):
            arcs.append(value)
            value = 0
    return ".".join(str(a) for a in arcs)


def _pem_to_der(pem_text: str, label: str) -> bytes:
    begin = f"-----BEGIN {label}-----"
    end = f"-----END {label}-----"
    lines = pem_text.strip().splitlines()
    in_block = False
    b64_lines = []
    for line in lines:
        t = line.strip()
        if t == begin:
            in_block = True
            continue
        if t == end:
            break
        if in_block and t:
            b64_lines.append(t)
    if not b64_lines:
        raise ValueError("invalid pem")
    return base64.b64decode("".join(b64_lines))


def bootstrap_ca_artifacts(out_dir: str = "keys/ca") -> dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)

    root_priv, root_cert = create_root_ca()
    with open(os.path.join(out_dir, "root_ca.crt.pem"), "w", encoding="utf-8") as f:
        f.write(root_cert.to_pem())

    root_pw = os.getenv("CA_ROOT_KEY_PASSWORD") or secrets.token_urlsafe(32)
    root_storage = SecureKeyStorage(filepath=os.path.join(out_dir, "root_ca_key_secure.json"))
    root_storage.encrypt_and_save({"private_key": root_priv, "public_key": root_cert.subject_public_key_hex}, root_pw)
    if not os.getenv("CA_ROOT_KEY_PASSWORD"):
        with open(os.path.join(out_dir, "root_ca_key_password.txt"), "w", encoding="utf-8") as f:
            f.write(root_pw)

    merchant_priv, merchant_pub = sm2_generate_keypair()
    merchant_csr = create_csr(
        subject_common_name="Merchant",
        subject_organization="Secure Ecommerce",
        subject_country="CN",
        subject_private_key_hex=merchant_priv,
        subject_public_key_hex=merchant_pub,
    )
    with open(os.path.join(out_dir, "merchant.csr.pem"), "w", encoding="utf-8") as f:
        f.write(merchant_csr.to_pem())
    with open(os.path.join(out_dir, "merchant_private_key.hex"), "w", encoding="utf-8") as f:
        f.write(merchant_priv)

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
    with open(os.path.join(out_dir, "merchant.crt.pem"), "w", encoding="utf-8") as f:
        f.write(merchant_cert.to_pem())

    user_priv, user_pub = sm2_generate_keypair()
    user_csr = create_csr(
        subject_common_name="User",
        subject_organization="Secure Ecommerce",
        subject_country="CN",
        subject_private_key_hex=user_priv,
        subject_public_key_hex=user_pub,
    )
    with open(os.path.join(out_dir, "user.csr.pem"), "w", encoding="utf-8") as f:
        f.write(user_csr.to_pem())
    with open(os.path.join(out_dir, "user_private_key.hex"), "w", encoding="utf-8") as f:
        f.write(user_priv)

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
    with open(os.path.join(out_dir, "user.crt.pem"), "w", encoding="utf-8") as f:
        f.write(user_cert.to_pem())

    return {
        "root_ca_cert": os.path.join(out_dir, "root_ca.crt.pem"),
        "root_ca_key_secure": os.path.join(out_dir, "root_ca_key_secure.json"),
        "merchant_cert": os.path.join(out_dir, "merchant.crt.pem"),
        "merchant_csr": os.path.join(out_dir, "merchant.csr.pem"),
        "merchant_key_hex": os.path.join(out_dir, "merchant_private_key.hex"),
        "user_cert": os.path.join(out_dir, "user.crt.pem"),
        "user_csr": os.path.join(out_dir, "user.csr.pem"),
        "user_key_hex": os.path.join(out_dir, "user_private_key.hex"),
    }


if __name__ == "__main__":
    paths = bootstrap_ca_artifacts()
    for k, v in paths.items():
        print(f"{k}={v}")
