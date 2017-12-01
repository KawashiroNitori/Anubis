import asyncio
import datetime
from bson import objectid

from anubis import db
from anubis import constant
from anubis.model import problem
from anubis.model import contest
from anubis.model import domain
from anubis.model import queue
from anubis.service import bus
from anubis.util import argmethod
from anubis.util import validator
from anubis.model.adaptor import judge


PROJECTION_PUBLIC = {'code': 0}
PROJECTION_ALL = None


@argmethod.wrap
async def add(domain_id: str, pid: int, type: int, uid: int, lang: str, code: str,
              data_id: objectid.ObjectId=None, tid: objectid.ObjectId=None,
              hidden=False):
    code = code.strip()
    coll = db.Collection('record')
    rid = await coll.insert({
        'hidden': hidden,
        'status': constant.record.STATUS_WAITING,
        'time_ms': 0,
        'memory_kb': 0,
        'domain_id': domain_id,
        'pid': pid,
        'uid': uid,
        'lang': lang,
        'code': code,
        'tid': tid,
        'data_id': data_id,
        'type': type
    })
    post_coros = []
    pdoc = await problem.get(domain_id=domain_id, pid=pid)
    if pdoc['judge_mode'] == constant.record.MODE_SUBMIT_ANSWER:
        await judge.judge_answer(domain_id, rid, pdoc, code)
    else:
        validator.check_lang(lang)
        post_coros.extend([queue.publish('judge', rid=rid),
                           bus.publish('record_change', rid)])
    if type == constant.record.TYPE_SUBMISSION:
        post_coros.extend([problem.inc(domain_id, pid, 'num_submit', 1),
                           problem.inc_status(domain_id, pid, uid, 'num_submit', 1),
                           domain.inc_user(domain_id, uid, num_submit=1)])
    await asyncio.gather(*post_coros)
    return rid


@argmethod.wrap
async def get(record_id: objectid.ObjectId, projection=PROJECTION_ALL):
    coll = db.Collection('record')
    return await coll.find_one(record_id, projection=projection)


async def remove_property(record_id: objectid.ObjectId, property_name: str):
    coll = db.Collection('record')
    return await coll.find_one_and_update(filter={'_id': record_id},
                                          update={'$unset': {property_name: ''}})


@argmethod.wrap
async def rejudge(record_id: objectid.ObjectId, enqueue: bool=True):
    coll = db.Collection('record')
    doc = await coll.find_one_and_update(filter={'_id': record_id},
                                         update={'$unset': {'judge_uid': '',
                                                            'judge_at': '',
                                                            'compiler_texts': '',
                                                            'judge_texts': '',
                                                            'cases': ''},
                                                 '$set': {'status': constant.record.STATUS_WAITING,
                                                          'time_ms': 0,
                                                          'memory_kb': 0,
                                                          'rejudged': True}},
                                         return_document=False)
    post_coros = []
    pdoc = await problem.get(doc['domain_id'], doc['pid'])
    if pdoc['judge_mode'] == constant.record.MODE_SUBMIT_ANSWER:
        await judge.judge_answer(doc['domain_id'], record_id, pdoc, doc['code'])
    else:
        post_coros.append(bus.publish('record_change', doc['_id']))
        if enqueue:
            post_coros.append(queue.publish('judge', rid=doc['_id']))
    await asyncio.gather(*post_coros)


@argmethod.wrap
async def rejudge_all():
    coll = db.Collection('record')
    records = await coll.find().to_list(None)
    for record in records:
        await rejudge(record['_id'])


@argmethod.wrap
async def rejudge_for_contest(domain_id: str, tid: int):
    async for rdoc in get_multi(domain_id=domain_id, tid=tid, type=constant.record.TYPE_SUBMISSION):
        await rejudge(rdoc['_id'])


@argmethod.wrap
async def rejudge_problem_for_contest(domain_id: str, tid: int, pid: int):
    async for rdoc in get_multi(domain_id=domain_id, tid=tid, pid=pid, type=constant.record.TYPE_SUBMISSION):
        await rejudge(rdoc['_id'])


@argmethod.wrap
def get_all_multi(end_id: objectid.ObjectId=None, get_hidden: bool=False, *, projection=None, **kwargs):
    coll = db.Collection('record')
    query = {**kwargs, 'hidden': False if not get_hidden else {'$gte': False}}
    if end_id:
        query['_id'] = {'$lt': end_id}
    return coll.find(query, projection=projection)


@argmethod.wrap
def get_multi(get_hidden: bool=False, projection=None, **kwargs):
    coll = db.Collection('record')
    kwargs['hidden'] = False if not get_hidden else {'$gte': False}
    return coll.find(kwargs, projection=projection)


@argmethod.wrap
async def get_count(begin_id: objectid.ObjectId=None):
    coll = db.Collection('record')
    query = {}
    if begin_id:
        query['_id'] = {'$gte': begin_id}
    return await coll.find(query).count()


@argmethod.wrap
def get_problem_multi(domain_id: str, pid: int, get_hidden: bool=False, type: int=None, *, projection=None):
    coll = db.Collection('record')
    query = {'hidden': False if not get_hidden else {'$gte': False},
             'domain_id': domain_id, 'pid': pid}
    if type is not None:
        query['type'] = type
    return coll.find(query, projection=projection)


@argmethod.wrap
def get_user_in_problem_multi(uid: int, domain_id: str, pid: int, get_hidden: bool=False,
                              type: int=None, *, projection=None):
    coll = db.Collection('record')
    query = {'hidden': False if not get_hidden else {'$gte': False},
             'domain_id': domain_id, 'pid': pid, 'uid': uid}
    if type is not None:
        query['type'] = type
    return coll.find(query, projection=projection)


async def get_dict(rids, *, get_hidden: bool=False, projection=None):
    query = {'_id': {'$in': list(set(rids))}}
    result = dict()
    async for rdoc in get_multi(**query, get_hidden=get_hidden, projection=projection):
        result[rdoc['_id']] = rdoc
    return result


@argmethod.wrap
async def begin_judge(record_id: objectid.ObjectId, judge_uid: int, status: int):
    coll = db.Collection('record')
    doc = await coll.find_one_and_update(filter={'_id': record_id},
                                         update={'$set': {'status': status,
                                                          'judge_uid': judge_uid,
                                                          'judge_at': datetime.datetime.utcnow(),
                                                          'compiler_texts': [],
                                                          'judge_texts': [],
                                                          'cases': [],
                                                          'progress': 0.0}},
                                         return_document=True)
    return doc


@argmethod.wrap
async def next_judge(record_id: objectid.ObjectId, judge_uid: int, **kwargs):
    coll = db.Collection('record')
    doc = await coll.find_one_and_update(filter={'_id': record_id},
                                         update=kwargs,
                                         return_document=True)
    return doc


@argmethod.wrap
async def end_judge(record_id: objectid.ObjectId, judge_uid: int,
                    status: int, time_ms: int, memory_kb: int):
    coll = db.Collection('record')
    doc = await coll.find_one_and_update(filter={'_id': record_id},
                                         update={'$set': {'status': status,
                                                          'time_ms': time_ms,
                                                          'memory_kb': memory_kb},
                                                 '$unset': {'progress': ''}},
                                         return_document=True)
    return doc


@argmethod.wrap
async def create_indexes():
    coll = db.Collection('record')
    await coll.create_index([('hidden', 1),
                             ('_id', -1)])
    await coll.create_index([('hidden', 1),
                             ('uid', 1),
                             ('_id', -1)])
    await coll.create_index([('hidden', 1),
                             ('domain_id', 1),
                             ('pid', 1),
                             ('uid', 1),
                             ('_id', -1)])
    # for job record
    await coll.create_index([('domain_id', 1),
                             ('pid', 1),
                             ('uid', 1),
                             ('type', 1),
                             ('_id', 1)])
    await coll.create_index([('domain_id', 1),
                             ('pid', 1),
                             ('type', 1),
                             ('_id', 1)])
    # TODO: Add more indexes.


if __name__ == '__main__':
    argmethod.invoke_by_args()
