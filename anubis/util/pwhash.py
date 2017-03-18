import base64
import binascii
import functools
import hashlib
import os

from anubis import error
from anubis.util import argmethod


def _md5(s):
    return hashlib.md5(s.encode()).hexdigest()


def _sha1(s):
    return hashlib.sha1(s.encode()).hexdigest()


def _b64encode(s):
    return base64.b64encode(s.encode()).decode()


def _b64decode(s):
    return base64.b64decode(s.encode()).decode()


@argmethod.wrap
def gen_salt(byte_length: int=20):
    return binascii.hexlify(os.urandom(byte_length)).decode()


@argmethod.wrap
def gen_secret(byte_length: int=20):
    return _sha1(gen_salt(byte_length))


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
