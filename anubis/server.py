import logging
import asyncio
import logging.config
import os
import socket
import urllib.parse

from tornado import netutil
from tornado import process

from anubis.util import options

options.define('listen', default='http://localhost:8888', help='Server listening address.')
options.define('prefork', default=0, help='Number of prefork workers')
options.define('log_format',
               default=('%(log_color)s[%(levelname).1s '
                        '%(asctime)s %(module)s:%(lineno)d]%(reset)s %(message)s'), help='Log format.')
_logger = logging.getLogger(__name__)

def main():
    logging.config.dictConfig({
        'version': 1,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'colored',
            },
        },
        'formatters': {
            'colored': {
                '()': 'colorlog.ColoredFormatter',
                'format': options.options.log_format,
                'datefmt': '%y%m%d %H:%M:%S'
            }
        },
        'root': {
            'level': 'DEBUG' if options.options.debug else 'INFO',
            'handlers': ['console'],
        },
        'disable_existing_loggers': False,
    })
    process.fork_processes(options.options.prefork)
    _logger.info('Server listening on %s', options.options.listen)
    url = urllib.parse.urlparse(options.options.listen)
    if url.scheme is 'http':
        host, port_str = url.netloc.rsplit(':', 1)
        sock = netutil.bind_sockets(int(port_str), host, socket.AF_INET, reuse_port=True)
    elif url.scheme is 'unix':
        try:
            os.remove(url.path)
        except:
            pass
        sock = netutil.bind_unix_socket(url.path)
    else:
        _logger.error('Invalid listening scheme %s', url.scheme)
        return 1
    loop = asyncio.get_event_loop()
    loop.run_until_complete()