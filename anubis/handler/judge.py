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
from anubis.model.adaptor import judge
from anubis.service import bus
from anubis.handler import base

_logger = logging.getLogger(__name__)


@app.route('/judge/playground', 'judge_playground')
class JudgePlaygroundHandler(base.Handler):
    @base.require_priv(builtin.JUDGE_PRIV)
    async def get(self):
        self.render('judge_playground.html')


@app.route('/judge/{rid}/cancel', 'judge_cancel')
class RecordCancelHandler(base.Handler):
    @base.route_argument
    @base.post_argument
    @base.require_csrf_token
    @base.sanitize
    async def post(self, *, rid: objectid.ObjectId, message: str = ''):
        rdoc = await record.get(rid)
        if rdoc['domain_id'] == self.domain_id:
            self.check_perm(builtin.PERM_REJUDGE)
        else:
            self.check_priv(builtin.PRIV_REJUDGE)
        await record.rejudge(rdoc['_id'], False)
        await record.begin_judge(rid, self.user['_id'],
                                 constant.record.STATUS_FETCHED)
        await record.next_judge(rid, self.user['_id'], **{'$push': {'judge_text': message}})
        rdoc = await record.end_judge(rid, self.user['_id'],
                                      constant.record.STATUS_CANCELLED, 0, 0)
        await judge.post_judge(rdoc)
        self.json_or_redirect(self.referer_or_main)


@app.route('/judge/heartbeat', 'judge_heartbeat')
class JudgeHeartbeatHandler(base.Handler):
    @base.require_priv(builtin.JUDGE_PRIV)
    async def get(self):
        self.json({'status': self.user.get('status', constant.record.STATUS_WAITING)})


@app.connection_route('/judge/consume-conn', 'judge_consume-conn')
class JudgeNotifyConnection(base.Connection):
    @base.require_priv(builtin.PRIV_READ_RECORD_CODE | builtin.PRIV_WRITE_RECORD)
    async def on_open(self):
        self.rids = {}  # delivery_tag -> rid
        bus.subscribe(self.on_problem_data_change, ['problem_data_change'])
        self.channel = await queue.consume('judge', self._on_queue_message)
        asyncio.ensure_future(self.channel.close_event.wait()).add_done_callback(lambda _: self.close())

    async def on_problem_data_change(self, e):
        domain_id_pid = dict(e['value'])
        self.send(event=e['key'], **domain_id_pid)

    async def _on_queue_message(self, tag, *, rid):
        # TODO(iceboy): Error handling?
        rdoc = await record.begin_judge(rid, self.user['_id'], constant.record.STATUS_FETCHED)
        if rdoc:
            self.rids[tag] = rdoc['_id']
            self.send(rid=str(rdoc['_id']), tag=tag, pid=str(rdoc['pid']), domain_id=rdoc['domain_id'],
                      lang=rdoc['lang'], code=rdoc['code'], type=rdoc['type'])
            await bus.publish('record_change', rdoc['_id'])
        else:
            # Record not found, eat it.
            await self.channel.basic_client_ack(tag)

    async def on_message(self, *, key, tag, **kwargs):
        if key == 'next':
            rid = self.rids[tag]
            update = {}
            if 'status' in kwargs:
                update.setdefault('$set', {})['status'] = int(kwargs['status'])
            if 'compiler_text' in kwargs:
                update.setdefault('$push', {})['compiler_texts'] = str(kwargs['compiler_text'])
            if 'judge_text' in kwargs:
                update.setdefault('$push', {})['judge_texts'] = str(kwargs['judge_text'])
            if 'case' in kwargs:
                update.setdefault('$push', {})['cases'] = {
                    'status': int(kwargs['case']['status']),
                    'time_ms': int(kwargs['case']['time_ms']),
                    'memory_kb': int(kwargs['case']['memory_kb']),
                    'judge_text': str(kwargs['case']['judge_text']),
                }
            if 'progress' in kwargs:
                update.setdefault('$set', {})['progress'] = float(kwargs['progress'])
            await record.next_judge(rid, self.user['_id'], **update)
            await bus.publish('record_change', rid)
        elif key == 'end':
            rid = self.rids.pop(tag)
            rdoc, _ = await asyncio.gather(record.end_judge(rid, self.user['_id'],
                                                            int(kwargs['status']),
                                                            int(kwargs['time_ms']),
                                                            int(kwargs['memory_kb'])),
                                           self.channel.basic_client_ack(tag))
            await judge.post_judge(rdoc)
        elif key == 'nack':
            await self.channel.basic_client_nack(tag)

    async def on_close(self):
        async def close():
            async def reset_record(rid):
                await record.end_judge(rid, self.user['_id'], self.id,
                                       constant.record.STATUS_WAITING, 0, 0, 0)
                await bus.publish('record_change', rid)

            await asyncio.gather(*[reset_record(rid) for rid in self.rids.values()])
            await self.channel.close()

        asyncio.get_event_loop().create_task(close())


@app.route('/judge/main', 'judge_main')
class JudgeMainHandler(base.OperationHandler):
    @base.require_priv(builtin.JUDGE_PRIV)
    @base.sanitize
    async def post_begin(self, *, rid: objectid.ObjectId, status: int):
        rdoc = await record.begin_judge(rid, self.user['_id'], status)
        if rdoc:
            await bus.publish('record_change', str(rid))
        await user.update(self.user['_id'], status={'code': constant.record.STATUS_FETCHED,
                                                    'rid': rid})
        self.json(rdoc)

    @base.require_priv(builtin.JUDGE_PRIV)
    async def post_next(self, *, rid: objectid.ObjectId, **kwargs):
        rid = objectid.ObjectId(rid)
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
                'judge_text': str(kwargs.get('case_judge_text', '')),
            }
        if 'progress' in kwargs:
            update.setdefault('$set', {})['progress'] = float(kwargs['progress'])
        rdoc = await record.next_judge(record_id=rid, judge_uid=self.user['_id'], **update)
        await bus.publish('record_change', str(rid))
        if 'status' in kwargs:
            await user.update(self.user['_id'], status={'code': kwargs['status'],
                                                        'rid': rid})
        self.json(rdoc)

    @base.require_priv(builtin.JUDGE_PRIV)
    @base.sanitize
    async def post_end(self, *, rid: objectid.ObjectId, status: int, time_ms: int, memory_kb: int):
        rdoc = await record.end_judge(rid, self.user['_id'], status, time_ms, memory_kb)
        await judge.post_judge(rdoc)
        await user.update(self.user['_id'], status={'code': constant.record.STATUS_WAITING})
        self.json(rdoc)
