import asyncio
import itertools
from bson import objectid

from anubis import constant
from anubis import error
from anubis import db
from anubis.model import builtin
from anubis.model import domain
from anubis.model import fs
from anubis.util import argmethod
from anubis.util import validator


STORE_DOMAIN_ID = builtin.DOMAIN_ID_SYSTEM


@argmethod.wrap
async def add(desc: str, file_id: objectid.ObjectId, owner_uid: int, length: int):
    validator.check_title(desc)
    coll = db.Collection('userfile')
    fid = objectid.ObjectId()
    doc = {'_id': fid,
           'domain_id': STORE_DOMAIN_ID,
           'content': desc,
           'owner_uid': owner_uid,
           'file_id': file_id,
           'length': length}
    await coll.insert_one(doc)
    return fid


@argmethod.wrap
async def get(fid: objectid.ObjectId):
    coll = db.Collection('userfile')
    doc = await coll.find_one({'domain_id': STORE_DOMAIN_ID, '_id': fid})
    if not doc:
        raise error.UserFileNotFoundError(fid)
    return doc


@argmethod.wrap
async def delete(fid: objectid.ObjectId):
    doc = await get(fid)
    coll = db.Collection('userfile')
    result = await coll.delete_one({'domain_id': STORE_DOMAIN_ID, '_id': fid})
    result = bool(result.deleted_count)
    if result:
        await fs.unlink(doc['file_id'])
    return result


def get_multi(projection=None, **kwargs):
    coll = db.Collection('userfile')
    return coll.find({'domain_id': STORE_DOMAIN_ID, **kwargs}, projection=projection)


async def get_dict(fids, *, projection=None):
    result = dict()
    if not fids:
        return result
    async for doc in get_multi(_id={'$in': list(set(fids))},
                               projection=projection):
        result[doc['_id']] = doc
    return result


@argmethod.wrap
async def get_usage(uid: int):
    dudoc = await domain.get_user(STORE_DOMAIN_ID, uid)
    if not dudoc:
        return 0
    return dudoc.get('usage_userfile', 0)


@argmethod.wrap
async def inc_usage(uid: int, usage: int, quota: int):
    return await domain.inc_user_usage(STORE_DOMAIN_ID, uid, 'usage_userfile', usage, quota)


@argmethod.wrap
async def dec_usage(uid: int, usage: int):
    return await domain.inc_user(STORE_DOMAIN_ID, uid, usage_userfile=-usage)


if __name__ == '__main__':
    argmethod.invoke_by_args()
