import logging
from os import path

from tornado import web

from anubis.util import options

options.define('debug', default=False, help='Enable debug mode.')
options.define('static', default=True, help='Serve static files.')
options.define('ip_header', default='X-Forwarded-For', help='Header name for remote IP.')
options.define('unsaved_session_expire_seconds', default=43200,
               help='Expire time for unsaved session, in seconds.')
options.define('saved_session_expire_seconds', default=2592000,
               help='Expire time for saved session, in seconds.')
options.define('cookie_domain', default=None, help='Cookie domain.')
options.define('cookie_secure', default=False, help='Enable secure cookie flag.')
options.define('registration_token_expire_seconds', default=86400,
               help='Expire time for registration token, in seconds.')
options.define('lostpass_token_expire_seconds', default=3600,
               help='Expire time for lostpass token, in seconds.')
options.define('changemail_token_expire_seconds', default=3600,
               help='Expire time for changemail token, in seconds.')
options.define('url_prefix', default='http://localhost', help='URL prefix.')
options.define('cdn_prefix', default='/', help='CDN prefix.')

_logger = logging.getLogger(__name__)

class Application(web.Application):
    def __init__(self):
        super().__init__(debug=options.options.debug)
        globals()[self.__class__.__name__] = lambda: self

    translation_path = path.join(path.dirname(__file__), 'locale')
    locale.loa
