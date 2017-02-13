import asyncio
import collections
import functools
import logging

from anubis import db
from anubis import constant
from anubis.model import domain
from anubis.model import builtin
from anubis.model import problem
from anubis.model import record
from anubis.model import user
from anubis.util import argmethod
from anubis.util import domainjob


_logger = logging.getLogger(__name__)


@argmethod.wrap
async def user_in_problem(uid: int, domain_id: str, pid: int):
    psdoc = await problem.rev_init_status(domain_id, pid, uid)
    rdocs = record.get_multi(uid=uid, domain_id=domain_id, pid=pid,
                             type=constant.record.TYPE_SUBMISSION,
                             projection={'_id': 1, 'uid': 1, 'status': 1, 'score': 1}).sort('_id', 1)
    new_psdoc = {'num_submit': 0, 'status': 0}
    async for rdoc in rdocs:
        new_psdoc['num_submit'] += 1
        if new_psdoc['status'] != constant.record.STATUS_ACCEPTED:
            new_psdoc['status'] = rdoc['status']
            new_psdoc['rid'] = rdoc['_id']
    _logger.info(repr(new_psdoc))
    if await problem.rev_set_status(domain_id, pid, uid, psdoc['rev'], **new_psdoc):
        delta_submit = new_psdoc['num_submit'] - psdoc.get('num_submit', 0)
        if new_psdoc['status'] == constant.record.STATUS_ACCEPTED \
                and psdoc.get('status', 0) != constant.record.STATUS_ACCEPTED:
            delta_accept = 1
        elif new_psdoc['status'] != constant.record.STATUS_ACCEPTED \
                and psdoc.get('status', 0) == constant.record.STATUS_ACCEPTED:
            delta_accept = -1
        else:
            delta_accept = 0
        post_coros = []
        if delta_submit != 0:
            post_coros.append(problem.inc(domain_id, pid, 'num_submit', delta_submit))
            post_coros.append(domain.inc_user(domain_id, uid, num_submit=delta_submit))
        if delta_accept != 0:
            post_coros.append(problem.inc(domain_id, uid, 'num_accept', delta_accept))
            post_coros.append(domain.inc_user(domain_id, uid, num_accept=delta_accept))
        if post_coros:
            await asyncio.gather(*post_coros)
