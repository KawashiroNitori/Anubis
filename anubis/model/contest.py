import collections
import datetime
import itertools

import functools
from bson import objectid
from pymongo import errors
from pymongo import ReturnDocument

from anubis import error
from anubis import db
from anubis.util import argmethod
from anubis.util import validator
from anubis.model import system

RULE_OI = 2
RULE_ACM = 3

TYPE_ONLINE = 1
TYPE_OFFLINE = 2

RULE_TEXTS = {
    RULE_OI: 'OI',
    RULE_ACM: 'ACM-ICPC',
}

Rule = collections.namedtuple('Rule', ['show_func', 'stat_func', 'status_sort', 'rank_func'])


def _oi_stat(tdoc, journal):
    detail = list(dict((j['pid'], j) for j in journal if j['pid'] in tdoc['pids']).values())
    return {'score': sum(d['score'] for d in detail), 'detail': detail}


def _acm_stat(tdoc, journal):
    naccept = collections.defaultdict(int)
    effective = {}
    for j in journal:
        if j['pid'] in tdoc['pids'] and not (j['pid'] in effective and effective[j['pid']]['accept']):
            effective[j['pid']] = j
            if not j['accept']:
                naccept[j['pid']] += 1

    def time(jdoc):
        real = jdoc['rid'].generation_time.replace(tzinfo=None) - tdoc['begin_at']
        penalty = datetime.timedelta(minutes=20) * naccept[jdoc['pid']]
        return (real + penalty).total_seconds()

    detail = [{**j, 'naccept': naccept[j['pid']], 'time': time(j)} for j in effective.values()]
    return {'accept': sum(int(d['accept']) for d in detail),
            'time': sum(d['time'] for d in detail if d['accept']),
            'detail': detail}


RULES = {
    RULE_ACM: Rule(lambda tdoc, now: now >= tdoc['begin_at'],
                   _acm_stat, [('accept', -1), ('time', 1)], functools.partial(enumerate,
                                                                               start=1)),
}


def convert_to_pid(pids, pid_letter):
    try:
        return pids[ord(pid_letter) - ord('A')]
    except IndexError:
        raise error.ContestProblemNotFoundError(pid_letter)


@argmethod.wrap
async def add(domain_id: str, title: str, content: str, owner_uid: int, rule: int,
              begin_at: lambda i: datetime.datetime.utcfromtimestamp(int(i)),
              end_at: lambda i: datetime.datetime.utcfromtimestamp(int(i)),
              pids=[], **kwargs):
    validator.check_title(title)
    validator.check_content(content)
    if rule not in RULES:
        raise error.ValidationError('rule')
    if begin_at >= end_at:
        raise error.ValidationError('begin_at', 'end_at')
    # TODO: should we check problem existance here?
    tid = system.inc_contest_counter()
    coll = db.Collection('contest')
    doc = {
        '_id': tid,
        'domain_id': domain_id,
        'title': title,
        'content': content,
        'owner_uid': owner_uid,
        'rule': rule,
        'begin_at': begin_at,
        'end_at': end_at,
        'pids': pids,
        'attend': 0,
        **kwargs,
    }
    await coll.insert(doc)
    return tid


@argmethod.wrap
async def get(domain_id: str, tid: int):
    coll = db.Collection('contest')
    return await coll.find_one({'domain_id': domain_id, '_id': tid})


def get_multi(domain_id: str, projection=None, **kwargs):
    coll = db.Collection('contest')
    return coll.find({'domain_id': domain_id, **kwargs}, projection=projection)


@argmethod.wrap
async def get_list(domain_id: str, projection=None):
    return await get_multi(domain_id=domain_id,
                           projection=projection).sort([('_id', -1)]).to_list(None)


@argmethod.wrap
async def attend(domain_id: str, tid: int, uid: int):
    #  TODO: check time.
    coll = db.Collection('contest.status')
    try:
        await coll.find_one_and_update(filter={'domain_id': domain_id,
                                               'tid': tid,
                                               'uid': uid,
                                               'attend': {'$ea': 0}},
                                       update={'$set': {'attend': 1}},
                                       upsert=True,
                                       return_document=ReturnDocument.AFTER)
    except errors.DuplicateKeyError:
        raise error.ContestAlreadyAttendedError(domain_id, tid, uid) from None
    coll = db.Collection('contest')
    return await coll.find_one_and_update(filter={'_id': tid},
                                          update={'$inc': {'attend': 1}},
                                          return_document=ReturnDocument.AFTER)


@argmethod.wrap
async def get_status(domain_id: str, tid: int, uid: int, projection=None):
    coll = db.Collection('contest.status')
    return await coll.find_one({'domain_id': domain_id, 'tid': tid, 'uid': uid},
                               projection=projection)


def get_multi_status(*, projection=None, **kwargs):
    coll = db.Collection('contest.status')
    return coll.find(kwargs, projection=projection)


async def get_dict_status(domain_id, uid, tids, *, projection=None):
    result = dict()
    async for tsdoc in get_multi_status(domain_id=domain_id,
                                        uid=uid,
                                        tid={'$in': list(set(tids))},
                                        projection=projection):
        result[tsdoc['tid']] = tsdoc
    return result


@argmethod.wrap
async def get_and_list_status(domain_id: str, tid: int, projection=None):
    # TODO: projection, pagination
    tdoc = await get(domain_id, tid)
    tsdocs = await get_multi_status(domain_id=domain_id,
                                    tid=tid,
                                    projection=projection
                                    ).sort(RULES[tdoc['rule']].status_sort).to_list(None)
    return tdoc, tsdocs


@argmethod.wrap
async def update_status(domain_id: str, tid: int, uid: int, rid: objectid.ObjectId,
                        pid: int, accept: bool):
    tdoc = await get(domain_id, tid)
    if pid not in tdoc['pids']:
        raise error.ValidationError('pid')

    coll = db.Collection('contest.status')
    tsdoc = await coll.find_one_and_update(filter={'domain_id': domain_id,
                                                   'tid': tid,
                                                   'uid': uid},
                                           update={
                                               '$push': {
                                                   'journal': {'rid': rid,
                                                               'pid': pid,
                                                               'accept': accept}
                                               },
                                               '$inc': {'rev': 1}},
                                           upsert=True,
                                           return_document=ReturnDocument.AFTER)
    if 'attend' not in tsdoc or not tsdoc['attend']:
        raise error.ContestNotAttendedError(domain_id, tid, uid)

    # Sort and uniquify journal of the contest status, by rid.
    key_func = lambda j: j['rid']
    journal = [list(g)[-1]
               for _, g in itertools.groupby(sorted(tsdoc['journal'], key=key_func), key=key_func)]
    stats = RULES[tdoc['rule']].stat_func(tdoc, journal)
    tsdoc = await coll.find_one_and_update(filter={'domain_id': domain_id,
                                                   'tid': tid,
                                                   'uid': uid,
                                                   'rev': tsdoc['rev']},
                                           update={'$set': {'journal': journal, **stats}, '$inc': {'rev': 1}},
                                           return_document=ReturnDocument.AFTER)
    return tsdoc


if __name__ == '__main__':
    argmethod.invoke_by_args()

