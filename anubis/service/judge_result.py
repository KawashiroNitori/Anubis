import asyncio
import logging
import bson

from anubis import mq
from anubis import constant
from anubis.model import record
from anubis.model import domain
from anubis.model import problem
from anubis.service import bus

_logger = logging.getLogger(__name__)


async def init():
    channel = await _consume()
    asyncio.get_event_loop().create_task(_work(channel))


async def _consume():
    channel = await mq.channel('judge_result')
    await channel.queue_declare('judge_result')

    await channel.basic_consume(_on_message, 'judge_result')
    return channel


async def _work(channel):
    while True:
        await channel.close_event.wait()
        _logger.warning('Message queue channel died, waiting for retry.')
        await asyncio.sleep(2)
        try:
            channel = await _consume()
        except Exception as e:
            _logger.exception(e)


async def _on_message(channel, body, envelope, properties):
    body = bson.BSON.decode(body)
    key = body['key']

    if key == 'begin':
        rid = body['rid']
        judge_uid = body['judge_uid']
        status = body['status']
        rdoc = await record.begin_judge(rid, judge_uid, status)
        if rdoc:
            await bus.publish('record_change', rid)

    elif key == 'next':
        rid = body['rid']
        update = {}
        if 'status' in body:
            update.setdefault('$set', {})['status'] = int(body['status'])
        if 'compiler_text' in body:
            update.setdefault('$push', {})['compiler_texts'] = str(body['compiler_text'])
        if 'judge_text' in body:
            update.setdefault('$push', {})['judge_texts'] = str(body['judge_text'])
        if 'case' in body:
            update.setdefault('$push', {})['cases'] = {
                'status': int(body['case']['status']),
                'time_ms': int(body['case']['time_ms']),
                'memory_kb': int(body['case']['memory_kb']),
                'judge_text': str(body['case']['judge_text']),
            }
        if 'progress' in body:
            update.setdefault('$set', {})['progress'] = float(body['progress'])
        await record.next_judge(rid, body['judge_uid'], **update)
        await bus.publish('record_change', rid)

    elif key == 'end':
        rid = body['rid']
        rdoc = await record.end_judge(rid, body['judge_uid'],
                                      int(body['status']),
                                      int(body['time_ms']),
                                      int(body['memory_kb']))

        accept = True if rdoc['status'] == constant.record.STATUS_ACCEPTED else False
        post_coros = [bus.publish('record_change', rid)]
        if rdoc['type'] == constant.record.TYPE_SUBMISSION:

            if await problem.update_status(rdoc['domain_id'], rdoc['pid'], rdoc['uid'],
                                           rdoc['_id'], rdoc['status']):
                post_coros.append(problem.inc(rdoc['domain_id'], rdoc['pid'], 'num_accept', 1))
                post_coros.append(domain.inc_user(rdoc['domain_id'], rdoc['uid'], num_accept=1))

            """
            if rdoc['tid']:
                post_coros.append(contest.update_status(rdoc['domain_id'], rdoc['tid'], rdoc['uid'],
                                                        rdoc['_id'], rdoc['pid'], accept, rdoc['score']))
            if accept:
                post_coros.append(training.update_status_by_pid(rdoc['domain_id'],
                                                                rdoc['uid'], rdoc['pid']))
            """
        await asyncio.gather(*post_coros)

    await channel.basic_client_ack(envelope.delivery_tag)



