import base64
import json
import os
import pprint
import sys
import traceback

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


def decrypt(b64_cipher: str, priv_key: str):
    priv_key = RSA.importKey(priv_key)
    cipher = base64.b64decode(b64_cipher)
    encrypted_aes_iv = cipher[:256]
    encrypted_plain = cipher[256:]

    aes_iv = priv_key.decrypt(encrypted_aes_iv)
    iv = aes_iv[:AES.block_size]
    aes_key = aes_iv[AES.block_size:]
    aes = AES.new(aes_key, AES.MODE_CBC, iv)
    plain = aes.decrypt(encrypted_plain)
    # remove padding
    plain = plain[:-plain[-1]].decode('utf8')
    return plain


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('{0}: Need private key file.'.format(sys.argv[0]))
        exit(1)
    priv_file = open(sys.argv[1])
    priv_key = priv_file.read()
    priv_file.close()
    try:
        cipher = input()
        plain = decrypt(cipher, priv_key)
        info = json.loads(plain)
        pprint.pprint(info)
        print('\nTrackback:')
        print(info['exc_stack'])
    except Exception as e:
        traceback.print_exc()
