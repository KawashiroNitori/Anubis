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
                post_coros.append(domain.inc_user(rdoc['domain_id'], rdoc['uid'],num_accept=1))
        else:
            await job.record.user_in_problem(rdoc['uid'], rdoc['domain_id'], rdoc['pid'])
    await asyncio.gather(*post_coros)


@app.route('/judge/playground', 'judge_playground')
class JudgePlaygroundHandler(base.Handler):
    @base.require_priv(builtin.PRIV_READ_RECORD_CODE | builtin.PRIV_WRITE_RECORD
                       | builtin.PRIV_READ_PRETEST_DATA | builtin.PRIV_READ_PROBLEM_DATA)
    async def get(self):
        self.render('judge_playground.html')


@app.route('/judge/noop', 'judge_noop')
class JudgeNoopHandler(base.Handler):
    @base.require_priv(builtin.JUDGE_PRIV)
    async def get(self):
        self.json({})


@app.route('/judge/datalist')
