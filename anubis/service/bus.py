import asyncio
import logging
import pprint

import bson

from anubis import mq
from anubis.util import argmethod

__logger = logging.getLogger(__name__)
_subscribers = {}


async def init():
    channel = await _consume()
    asyncio.get_event_loop().create_task(_work(channel))


async def _consume():
    channel = await mq.channel('bus')
    await channel.exchange_declare('bus', 'fanout', auto_delete=False)
    queue = await channel.queue_declare(exclusive=False, auto_delete=True)
    queue_name = queue['queue']
    await channel.queue_bind(queue_name, 'bus', '')

    async def on_message(t_channel, body, envelope, properties):
        e = bson.BSON.decode(body)
        coroutines = [subscriber(e)
                      for subscriber, key_set in _subscribers.items()
                      if e['key'] in key_set]
        await asyncio.gather(*coroutines)
        await t_channel.basic_client_ack(envelope.delivery_tag)

    await channel.basic_consume(on_message, queue_name)
    return channel


async def _work(channel):
    while True:
        await channel.close_event.wait()
        __logger.warning('Message queue channel died, waiting for retry.')
        await asyncio.sleep(2)
        try:
            channel = await _consume()
        except Exception as e:
            __logger.exception(e)


@argmethod.wrap
async def publish(key: str, value: str):
    channel = await mq.channel('bus')
    await channel.basic_publish(bson.BSON.encode({'key': key, 'value': value}), 'bus', '')


def subscribe(callback, keys):
    """Subscribe a set of bus keys for a callback.

    Args:
        callback: coroutine function for bus callback.
        keys: list, set or tuple of object for event keys.
    """
    assert type(keys) in (set, list, tuple)
    _subscribers[callback] = keys


def unsubscribe(callback):
    """Unsubscribe buses for a callback.

    Args:
        callback: coroutine function for bus callback.
    """
    if callback in _subscribers:
        del _subscribers[callback]


@argmethod.wrap
async def tail():
    channel = await mq.channel('bus')
    await channel.exchange_declare('bus', 'fanout', auto_delete=True)
    queue = await channel.queue_declare(exclusive=True, auto_delete=True)
    queue_name = queue['queue']
    await channel.queue_bind(queue_name, 'bus', '')

    async def on_message(t_channel, body, envelope, properties):
        pprint.pprint(bson.BSON.decode(body))

    await channel.basic_consume(on_message, queue_name)
    await channel.close_event.wait()


if __name__ == '__main__':
    argmethod.invoke_by_args()
