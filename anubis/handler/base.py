import accept
import asyncio
import calendar
import functools
import hmac
import logging
import markupsafe
import pytz
import sockjs
from aiohttp import web

from anubis import app
from anubis import error
from anubis import template
from anubis.model import builtin
from anubis.model import user
from anubis.model.adaptor import setting

from anubis.util import json
from anubis.util import locale
from anubis.util import locale
from anubis.util import options

_logger = logging.getLogger(__name__)


class HandlerBase(setting.SettingMixin):
    NAME = None
    TITLE = None

    async def prepare(self):
        self.session = await self.update_session()
        self.domain_id = self.request.match_info.pop('domain_id', builtin.DOMAIN_ID_SYSTEM)
        if 'uid' in self.session:
            uid = self.session['uid']
            self.user, self.domain, self.domain_user = await asyncio.gather(
                user.get_by_uid(uid), doma
            )