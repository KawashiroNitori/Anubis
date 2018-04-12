import base64
import os

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA

_PUBLIC_KEY = ('-----BEGIN PUBLIC KEY-----\n'
               'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuvfhcdlYJwLWXdTrBCxq\n'
               'VCKSBPru2xko0i07tCgsHZ3oEd96VpB6o9NN0mJ1tPMK68upUAKeUgKNbxzannnR\n'
               'HQNKmmZau2+cJCZibd/HCFtUDRiof1RAsr+HY0Pe0G4f+9+h/Hfdo4GTqMnChViL\n'
               'BEEXGp55j+PakGKlcnByXyZeX9/ebqYUY63IOXOn8Cy4tkdawEDjFLv/6eSDXEIN\n'
               '44E+XEZ+IeLhFXzuZLHX3JiW/DK4kRoFTSqhW1QUFrmakNQQm5nUagI2bVzHdl7T\n'
               'V0bgaGT9J8/4E9ML+NmP2mxJrZ6p7zjM/K+MNU0WKQt8va6GD4S8ezTJnmBLpmii\n'
               'lQIDAQAB\n'
               '-----END PUBLIC KEY-----')


def encrypt(plain: bytes):
    # prepare AES cipher
    aes_key = os.urandom(32)
    iv = Random.new().read(AES.block_size)
    aes_cipher = AES.new(aes_key, AES.MODE_CBC, iv)

    # prepare RSA cipher
    rsa_cipher = RSA.importKey(_PUBLIC_KEY)

    # encrypt AES key
    encrypted_aes = rsa_cipher.encrypt(iv + aes_key, '')[0]

    # use AES to encrypt plain
    padding_length = AES.block_size - len(plain) % AES.block_size
    padded_plain = plain + bytes([padding_length] * padding_length)
    encrypted_plain = aes_cipher.encrypt(padded_plain)

    result = base64.b64encode(encrypted_aes + encrypted_plain).decode('utf8')
    return result
