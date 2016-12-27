import base64
import binascii
import functools
import hashlib
import os

from anubis import error
from anubis.util import argmethod


@argmethod.wrap
def gen_salt(byte_length: int = 20):
    return binascii.hexlify(os.urandom(byte_length)).decode()


@argmethod.wrap
def hash_password(password: str, salt: str):
    dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return binascii.hexlify(dk).decode()


@argmethod.wrap
@functools.lru_cache()
def check(password: str, salt: str, hash_str: str):
    return hash_str == hash_password(password, salt)


if __name__ == '__main__':
    argmethod.invoke_by_args()
