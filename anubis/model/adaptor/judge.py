import asyncio
from bson import objectid

from anubis import constant
from anubis import job
from anubis.model import builtin
from anubis.model import problem
from anubis.model import record
from anubis.model import contest
from anubis.model import domain
from anubis.service import bus


async def post_judge(rdoc):
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


async def judge_answer(domain_id: str, rid: objectid.ObjectId, pdoc, answer: str):
    data = await problem.get_data(domain_id, pdoc['_id'])
    if data['data'] == answer:
        status = constant.record.STATUS_ACCEPTED
    else:
        status = constant.record.STATUS_WRONG_ANSWER
    rdoc = await record.end_judge(rid, builtin.UID_SYSTEM, status, 0, 0)
    await post_judge(rdoc)
