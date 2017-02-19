import asyncio
import calendar
import logging
from bson import objectid

from anubis import app
from anubis import constant
from anubis import job
from anubis.model import builtin
from anubis.model import domain
from anubis.model import opcount
from anubis.model import queue
from anubis.model import record
from anubis.model import user
from anubis.model import contest
from anubis.model import problem
from anubis.service import bus
from anubis.handler import base


_logger = logging.getLogger(__name__)


async def _post_judge(rdoc):
    accept = rdoc['status'] == constant.record.STATUS_ACCEPTED
    post_coros = [bus.publish('record_change', rdoc['_id'])]
    # TODO: ignore no effect statuses like system error...
    if rdoc['type'] == constant.record.TYPE_SUBMISSION:
        if accept:
            # TODO: send ac mail
            pass
        if rdoc['tid']:
            post_coros.append(contest.update_status(rdoc['domain_id'], rdoc['tid'], rdoc['uid'],
                                                    rdoc['_id'], rdoc['pid'], accept))
        if not rdoc.get('rejudged'):
            if await problem.update_status(rdoc['domain_id'], rdoc['pid'], rdoc['uid'],
                                           rdoc['_id'], rdoc['status']):
                post_coros.append(problem.inc(rdoc['domain_id'], rdoc['pid'], 'num_accept', 1))
                post_coros.append(domain.inc_user(rdoc['domain_id'], rdoc['uid'], num_accept=1))
        else:
            await job.record.user_in_problem(rdoc['uid'], rdoc['domain_id'], rdoc['pid'])
    await asyncio.gather(*post_coros)


@app.route('/judge/playground', 'judge_playground')
class JudgePlaygroundHandler(base.Handler):
    @base.require_priv(builtin.JUDGE_PRIV)
    async def get(self):
        self.render('judge_playground.html')


@app.route('/judge/heartbeat', 'judge_heartbeat')
class JudgeHeartbeatHandler(base.Handler):
    @base.require_priv(builtin.JUDGE_PRIV)
    async def get(self):
        self.json({'status': self.user['status']})


@app.route('/judge/{rid:[\da-f]{24}}', 'judge_main')
class JudgeMainHandler(base.OperationHandler):
    @base.require_priv(builtin.JUDGE_PRIV)
    @base.route_argument
    @base.post_argument
    @base.sanitize
    async def post_begin(self, rid, status: int):
        rdoc = await record.begin_judge(rid, self.user['_id'], status)
        if rdoc:
            await bus.publish('record_change', rid)
        await user.update(self.user['_id'], status={'code': constant.record.STATUS_FETCHED,
                                                    'rid': rid})
        self.json(rdoc)

    @base.require_priv(builtin.JUDGE_PRIV)
    @base.route_argument
    @base.post_argument
    @base.sanitize
    async def post_next(self, rid, **kwargs):
        update = {}
        if 'status' in kwargs:
            update.setdefault('$set', {})['status'] = int(kwargs['status'])
        if 'compiler_text' in kwargs:
            update.setdefault('$push', {})['compiler_texts'] = str(kwargs['compiler_text'])
        if 'judge_text' in kwargs:
            update.setdefault('$push', {})['judge_texts'] = str(kwargs['judge_text'])
        if 'case' in kwargs:
            update.setdefault('$push', {})['cases'] = {
                'status': int(kwargs['case_status']),
                'time_ms': int(kwargs['case_time_ms']),
                'memory_kb': int(kwargs['case_memory_kb']),
                'judge_text': str(kwargs['case_judge_text']),
            }
        if 'progress' in kwargs:
            update.setdefault('$set', {})['progress'] = float(kwargs['progress'])
        rdoc = await record.next_judge(rid, self.user['_id'], **update)
        await bus.publish('record_change', rid)
        if 'status' in kwargs:
            await user.update(self.user['_id'], status={'code': kwargs['status'],
                                                        'rid': rid})
        self.json(rdoc)

    @base.require_priv(builtin.JUDGE_PRIV)
    @base.route_argument
    @base.post_argument
    @base.sanitize
    async def post_end(self, rid, **kwargs):
        rdoc = await record.end_judge(rid, self.user['_id'],
                                      int(kwargs['status']),
                                      int(kwargs['time_ms']),
                                      int(kwargs['memory_kb']))
        await _post_judge(rdoc)
        await user.update(self.user['_id'], status={'code': constant.record.STATUS_WAITING})
        self.json(rdoc)
