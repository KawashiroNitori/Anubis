import asyncio
import datetime

from anubis import app
from anubis import error
from anubis import template
from anubis.model import builtin
from anubis.model import domain
from anubis.model import system
from anubis.model import token
from anubis.model import user
from anubis.util import options
from anubis.util import validator
from anubis.handler import base


@app.route('/register', 'user_register')
class UserRegisterHandler(base.Handler):
    @base.require_priv(builtin.PRIV_REGISTER_USER)
    async def get(self):
        self.render('user_register.html')

    @base.require_priv(builtin.PRIV_REGISTER_USER)
    @base.limit_rate('user_register', 3600, 60)
    @base.post_argument
    @base.route_argument
    @base.sanitize
    async def post(self, *, mail: str, uname: str, password: str, verify_password: str):
        validator.check_mail(mail)
        validator.check_name(uname)
        if await user.get_by_mail(mail):
            raise error.UserAlreadyExistError(mail)
        if await user.get_by_uname(uname):
            raise error.UserAlreadyExistError(uname)
        if password != verify_password:
            raise error.VerifyPasswordError()
        uid = await system.inc_user_counter()
        await user.add(uid, uname, password, mail, self.remote_ip)
        await self.update_session(new_saved=False, uid=uid)
        self.json_or_redirect(self.reverse_url('domain_main'))


@app.route('/lostpass', 'user_lostpass')
class UserLostPasswordHandler(base.Handler):
    @base.require_priv(builtin.PRIV_REGISTER_USER)
    async def get(self):
        self.render('user_lostpass.html')

    @base.require_priv(builtin.PRIV_REGISTER_USER)
    @base.limit_rate('user_register', 3600, 60)
    @base.post_argument
    @base.sanitize
    async def post(self, *, mail: str):
        validator.check_mail(mail)
        udoc = await user.get_by_mail(mail)
        if not udoc:
            raise error.UserNotFoundError(mail)
        rid, _ = await token.add(token.TYPE_LOSTPASS,
                                 options.options.lostpass_token_expire_seconds,
                                 uid=udoc['_id'])
        await self.send_mail(mail, 'Lost Password', 'user_lostpass_mail.html',
                             url=self.reverse_url('user_lostpass_with_code', code=rid),
                             uname=udoc['uname'])
        self.render('user_lostpass_mail_sent.html')


@app.route('/lostpass/{code}', 'user_lostpass_with_code')
class UserLostPasswordWithCodeHandler(base.Handler):
    TITLE = 'user_lostpass'

    @base.require_priv(builtin.PRIV_REGISTER_USER)
    @base.route_argument
    @base.sanitize
    async def get(self, *, code: str):
        tdoc = await token.get(code, token.TYPE_LOSTPASS)
        if not tdoc:
            raise error.InvalidTokenError(token.TYPE_LOSTPASS, code)
        udoc = await user.get_by_uid(tdoc['uid'])
        self.render('user_lostpass_with_code.html', uname=udoc['uname'])

    @base.require_priv(builtin.PRIV_REGISTER_USER)
    @base.route_argument
    @base.post_argument
    @base.sanitize
    async def post(self, *, code: str, password: str, verify_password: str):
        tdoc = await token.get(code, token.TYPE_LOSTPASS)
        if not tdoc:
            raise error.InvalidTokenError(token.TYPE_LOSTPASS, code)
        if password != verify_password:
            raise error.VerifyPasswordError()
        await user.set_password(tdoc['uid'], password)
        await token.delete(code, token.TYPE_LOSTPASS)
        self.json_or_redirect(self.reverse_url('domain_main'))


@app.route('/login', 'user_login')
class UserLoginHandler(base.Handler):
    async def get(self):
        if self.has_priv(builtin.PRIV_USER_PROFILE):
            self.redirect(self.reverse_url('domain_main'))
        else:
            self.render('user_login.html')

    @base.post_argument
    @base.sanitize
    async def post(self, *, uname: str, password: str, remember_me: bool=False):
        udoc = await user.check_password_by_uid(uname, password)
        if not udoc:
            raise error.LoginError(uname)
        await asyncio.gather(user.set_by_uid(udoc['_id'],
                                             login_at=datetime.datetime.utcnow(),
                                             login_ip=self.remote_ip),
                             self.update_session(new_saved=remember_me, uid=udoc['_id']))
        self.json_or_redirect(self.referer_or_main)


@app.route('/logout', 'user_logout')
class UserLogoutHandler(base.Handler):
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    async def get(self):
        self.render('user_logout.html')

    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.post_argument
    @base.require_csrf_token
    async def post(self):
        await self.delete_session()
        self.json_or_redirect(self.referer_or_main)



