import collections
import datetime
import itertools

from bson import objectid
from pymongo import errors
from anubis import error
from anubis import db
from anubis.util import argmethod
from anubis.util import validator


RULE_OI = 2
RULE_ACM = 3

RULE_TEXTS = {
    RULE_OI: 'OI',
    RULE_ACM: 'ACM-ICPC',
}

Rule = collections.namedtuple('Rule', ['show_func', 'stat_func', 'status_sort'])


def _oi_stat(tdoc, journal):
    detail = list(dict((j['pid'], j) for j in journal if j['pid'] in tdoc['pids']).values())
    return {'score': sum(d['score'] for d in detail), 'detail':detail}


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
    RULE_OI: Rule(lambda tdoc, now: now > tdoc['end_at'], _oi_stat, [('score', -1)]),
    RULE_ACM: Rule(lambda tdoc, now: now >= tdoc['begin_at'],
                   _acm_stat, [('accept', -1), ('time', 1)]),
}


@argmethod.wrap
async def add(domain_id: str, title: str, content: str, owner_uid: int, rule: int,
              begin_at: lambda i: datetime.datetime.utcfromtimestamp(int(i)),
              end_at: lambda i: datetime.datetime.utcfromtimestamp(int(i)),
              pids={}):
    validator.check_title(title)
    validator.check_content(content)
    if rule not in RULES:
        raise error.ValidationError('rule')
    if begin_at >= end_at:
        raise error.ValidationError('begin_at', 'end_at')
    # TODO: should we check problem existance here?
    coll = db.Collection('contest')
    doc = {

    }
    return await coll.insert()
