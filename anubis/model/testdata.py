from bson import objectid

from anubis import db
from anubis.util import argmethod

TYPE_TEST_DATA = 1
TYPE_PRETEST_DATA = 2


@argmethod.wrap
async def add(domain_id: str, data: list, owner_uid: int, type: int, pid: int, **kwargs):
    coll = db.Collection('testdata')
    doc = {
        'data': data,
        'owner_uid': owner_uid,
        'domain_id': domain_id,
        'type': type,
        'pid': pid,
        **kwargs
    }
    doc = await coll.insert(doc)
    return doc['_id']


@argmethod.wrap
async def get(domain_id: str, id: objectid.ObjectId):
    coll = db.Collection('testdata')
    return await coll.find_one({'domain_id': domain_id,
                                '_id': id})


@argmethod.wrap
async def edit(domain_id: str, id: objectid.ObjectId, **kwargs):
    coll = db.Collection('testdata')
    doc = await coll.find_one_and_update(filter={'domain_id': domain_id,
                                                 '_id': id},
                                         update={'$set': kwargs},
                                         return_document=True)
    return doc


@argmethod.wrap
async def delete(domain_id: str, id: objectid.ObjectId):
    coll = db.Collection('testdata')
    return await coll.delete_one({'domain_id': domain_id,
                                  '_id': id})


@argmethod.wrap
async def create_indexes():
    coll = db.Collection('testdata')
    await coll.create_index([('domain_id', 1),
                             ('_id', 1)], unique=True)


if __name__ == '__main__':
    argmethod.invoke_by_args()
