"""Authenticated field encryption; keys live outside the database and repository."""
import os

from cryptography.fernet import Fernet
from sqlalchemy.types import String, TypeDecorator

PREFIX = 'enc:v1:'


def card_cipher():
    key = os.getenv('BANK_CARD_ENCRYPTION_KEY', '')
    if not key:
        raise RuntimeError('BANK_CARD_ENCRYPTION_KEY is required for bank-card storage')
    return Fernet(key.encode('ascii'))


def encrypt_card(value):
    if value is None or value == '':
        return None
    return PREFIX + card_cipher().encrypt(str(value).encode('utf-8')).decode('ascii')


def decrypt_card(value):
    if not value:
        return None
    if not value.startswith(PREFIX):
        raise ValueError('Unmigrated bank-card data: run scripts/encrypt_stored_cards.py')
    return card_cipher().decrypt(value[len(PREFIX):].encode('ascii')).decode('utf-8')


class EncryptedBankCard(TypeDecorator):
    impl = String(512)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt_card(value)

    def process_result_value(self, value, dialect):
        return decrypt_card(value)
