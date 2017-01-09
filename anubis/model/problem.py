import datetime

from bson import objectid
from pymongo import errors

from anubis import constant
from anubis import db
from anubis import error
from anubis.model import fs
from anubis.model import system
from anubis.util import argmethod
from anubis.util import validator

MODE_COMPARE_CHAR_IGNORE_BLANK = 1
MODE_COMPARE_CHAR = 2
MODE_CUSTOM_JUDGE = 3


@argmethod.wrap
async def add(domain_id: str, title: str, content: str, owner_uid: int,
              time_ms: int, memory_kb: int, judge_mode: int,
              data: objectid.ObjectId = None,
              hidden: bool = False, **kwargs):
    validator.check_title(title)
    validator.check_content(content)
    pid = await system.inc_problem_counter()
    coll = db.Collection('problem')
    doc = {'_id': pid,
           'content': content,
           'owner_uid': owner_uid,
           'domain_id': domain_id,
           'title': title,
           'time_ms': time_ms,
           'memory_kb': memory_kb,
           'judge_mode': judge_mode,
           'data': data,
           'hidden': hidden,
           'num_submit': 0,
           'num_accept': 0,
           **kwargs}
    return await coll.insert(doc)


@argmethod.wrap
async def get(domain_id: str, pid: int, uid: int = None):
    coll = db.Collection('problem')
    pdoc = await coll.find_one({'domain_id': domain_id,
                                '_id': pid})
    if not pdoc:
        raise error.ProblemNotFoundError(domain_id, pid)
    return pdoc


@argmethod.wrap
async def edit(domain_id: str, pid: int, **kwargs):
    if 'title' in kwargs:
        validator.check_title(kwargs['title'])
    if 'content' in kwargs:
        validator.check_content(kwargs['content'])
    coll = db.Collection('problem')
    pdoc = await coll.find_one_and_update(filter={'domain_id': domain_id,
                                                  '_id': pid},
                                          update={'$set': kwargs},
                                          return_document=True)
    if not pdoc:
        raise error.ProblemNotFoundError(domain_id, pid)
    return pdoc


def get_multi(*, projection=None, **kwargs):
    coll = db.Collection('problem')
    return coll.find(kwargs, projection=projection)


async def get_dict(pids, *, projection=None):
    pquery = {'$or': [{'domain_id': e[0], '_id': e[1]} for e in set(pids)]}
    result = dict()
    async for pdoc in get_multi(**pquery, projection=projection).hint([('domain_id', 1),
                                                                       ('_id', 1)]):
        result[(pdoc['domain_id'], pdoc['_id'])] = pdoc
    return result


@argmethod.wrap
async def get_status(domain_id: str, pid: int, uid: int, projection=None):
    coll = db.Collection('problem.status')
    return await coll.find_one({'domain_id': domain_id,
                                'pid': pid,
                                'uid': uid},
                               projection=projection)


def get_multi_status(*, projection=None, **kwargs):
    coll = db.Collection('problem.status')
    return coll.find(kwargs, projection=projection)


async def get_dict_status(domain_id, uid, pids, *, projection=None):
    result = dict()
    async for psdoc in get_multi_status(domain_id=domain_id,
                                        uid=uid,
                                        pid={'$in': list(set(pids))},
                                        projection=projection):
        result[psdoc['pid']] = psdoc
    return result


async def get_data(domain_id, pid):
    pdoc = await get(domain_id, pid)
    if not pdoc.get('data', None):
        raise error.ProblemDataNotFoundError(domain_id, pid)
    return await fs.get(pdoc['data'])


@argmethod.wrap
async def get_data_md5(domain_id: str, pid: int):
    pdoc = await get(domain_id, pid)
    if not pdoc['data']:
        raise error.ProblemDataNotFoundError(domain_id, pid)
    return await fs.get_md5(pdoc['data'])


@argmethod.wrap
async def set_data(domain_id: str, pid: int, data: objectid.ObjectId):
    pdoc = await edit(domain_id, pid, data=data)
    if not pdoc:
        raise error.ProblemNotFoundError(domain_id, pid)
    return pdoc


@argmethod.wrap
async def set_hidden(domain_id: str, pid: int, hidden: bool):
    pdoc = await edit(domain_id, pid, hidden=hidden)
    if not pdoc:
        raise error.ProblemNotFoundError(domain_id, pid)
    return pdoc


@argmethod.wrap
async def inc(domain_id: str, pid: int, key: str, value: int):
    coll = db.Collection('problem')
    return await coll.find_one_and_update(filter={'domain_id': domain_id,
                                                  '_id': pid},
                                          update={'$inc': {key: value}},
                                          return_document=True)


@argmethod.wrap
async def update_status(domain_id: str, pid: int, uid: int, rid: objectid.ObjectId, status: int):
    coll = db.Collection('problem.status')
    try:
        return await coll.find_one_and_update(filter={'domain_id': domain_id,
                                                      'pid': pid,
                                                      'uid': uid,
                                                      'status': {'$ne': constant.record.STATUS_ACCEPTED}},
                                              update={'$set': {'status': status, 'rid': rid}},
                                              return_document=True,
                                              upsert=True)
    except errors.DuplicateKeyError:
        return None


@argmethod.wrap
async def create_indexes():
    coll = db.Collection('problem')
    await coll.create_index([('domain_id', 1),
                             ('_id', 1)], unique=True)

if __name__ == '__main__':
    argmethod.invoke_by_args()
