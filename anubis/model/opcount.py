import datetime
import time

from pymongo import errors

from anubis import db
from anubis import error
from anubis.util import argmethod


PREFIX_IP = 'ip-'
PREFIX_USER = 'user-'


@argmethod.wrap
async def inc(op: str, id: str, period_secs: int, max_operations: int):
    coll = db.Collection('op_count')
    cur_time = int(time.time())
    begin_at = datetime.datetime.utcfromtimestamp(cur_time - cur_time % period_secs)
    expire_at = begin_at + datetime.timedelta(seconds=period_secs)
    try:
        doc = await coll.find_one_and_update(filter={'id': id,
                                                     'begin_at': begin_at,
                                                     'expire_at': expire_at,
                                                     op: {'$not': {'$gte': max_operations}}},
                                             update={'$inc': {op: 1}},
                                             upsert=True,
                                             return_document=True)
        return doc
    except errors.DuplicateKeyError:
        raise error.OpCountExceededError(op, period_secs, max_operations)


@argmethod.wrap
async def create_indexes():
    coll = db.Collection('op_count')
    await coll.create_index([('id', 1),
                             ('begin_at', 1),
                             ('expire_at', 1)], unique=True)
    await coll.create_index('expire_at', expireAfterSeconds=0)


if __name__ == '__main__':
    argmethod.invoke_by_args()
