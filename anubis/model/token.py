import binascii
import datetime
import hashlib
import os

from anubis.util import argmethod
from anubis.util import json
from anubis import redis

TYPE_REGISTRATION = 1
TYPE_SAVED_SESSION = 2
TYPE_UNSAVED_SESSION = 3
TYPE_LOSTPASS = 4
TYPE_CHANGEMAIL = 5


def _get_id(id_binary):
    return hashlib.sha256(id_binary).digest()


@argmethod.wrap
async def add(token_type: int, expire_seconds: int, **kwargs):
    """Add a token.

    Args:
        token_type: type of the token.
        expire_seconds: expire time, in seconds.
        **kwargs: extra data.

    Returns:
        Tuple of (Token ID, token document).
    """
    id_binary = _get_id(os.urandom(32))
    id_hash = binascii.hexlify(id_binary).decode()
    now = datetime.datetime.utcnow()
    doc = {
        **kwargs,
        '_id': id_hash,
        'token_type': token_type,
        'create_at': now,
        'update_at': now,
        'expire_at': now + datetime.timedelta(seconds=expire_seconds)
    }
    db = await redis.database()
    await db.set('token_' + id_hash, json.encode(doc), expire=expire_seconds)
    return id_hash, doc


@argmethod.wrap
async def get(token_id: str, token_type: int):
    """Get a token.
    Args:
        token_id: token ID.
        token_type: type of the token.

    Returns:
        The token document, or None.
    """
    db = await redis.database()
    doc = await db.get('token_' + token_id)
    if doc:
        return json.decode(doc.decode())
    else:
        return None


@argmethod.wrap
async def update(token_id: str, token_type: int, expire_seconds: int, replace: bool=False, **kwargs):
    """Update a token.

    Args:
        token_id: token ID.
        token_type: type of the token.
        expire_seconds: expire time, in seconds.
        replace: if True, replace this key instead of update.
        **kwargs: extra data.

    Returns:
        The token document, or None.
    """
    db = await redis.database()
    assert 'token_type' not in kwargs
    now = datetime.datetime.utcnow()
    doc = await get(token_id, token_type)
    if not doc:
        return None
    if not replace:
        doc.update({**kwargs,
                    'token_type': token_type,
                    'update_at': now,
                    'expire_at': now + datetime.timedelta(seconds=expire_seconds)})
    else:
        doc = {**kwargs,
               'token_type': token_type,
               'update_at': now,
               'expire_at': now + datetime.timedelta(seconds=expire_seconds)}
    await db.set('token_' + token_id, json.encode(doc), expire=expire_seconds)
    return doc


@argmethod.wrap
async def delete(token_id: str, token_type: int):
    """Delete a token.
    Args:
        token_id: token ID.
        token_type: type of the token.

    Returns:
        True if deleted or False.
    """
    db = await redis.database()
    return await db.delete('token_' + token_id)


@argmethod.wrap
def gen_csrf_token():
    token_hash = _get_id(os.urandom(32))
    return binascii.hexlify(token_hash).decode()
