import aioredis

from anubis.util import options


options.define('redis_host', default='localhost', help='Redis hostname or IP address.')
options.define('redis_port', default=6379, help='Redis port.')
options.define('redis_index', default=1, help='Redis database index.')

_connection = None


async def _create_connect():
    global _connection
    if not _connection:
        _connection = await aioredis.create_redis(
            (options.options.redis_host, options.options.redis_port),
            db=options.options.redis_index
        )
    return _connection


async def database():
    return await _create_connect()
