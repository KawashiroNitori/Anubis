import asyncio
import datetime
import random
import re

from anubis import app
from anubis import error
from anubis import template
from anubis import constant
from anubis.model import builtin
from anubis.model import domain
from anubis.model import system
from anubis.model import token
from anubis.model import user
from anubis.model import problem
from anubis.model import discussion
from anubis.model import record
from anubis.model.adaptor import setting
from anubis.util import options
from anubis.util import validator
from anubis.handler import base


class UserSettingsMixin(object):
  def can_view(self, udoc, key):
    privacy = udoc.get('show_' + key, next(iter(setting.SETTINGS_BY_KEY['show_' + key].range)))
    return udoc['_id'] == self.user['_id'] \
           or (privacy == constant.setting.PRIVACY_PUBLIC and True) \
           or (privacy == constant.setting.PRIVACY_REGISTERED_ONLY
               and self.has_priv(builtin.PRIV_USER_PROFILE)) \
           or (privacy == constant.setting.PRIVACY_SECRET
               and self.has_priv(builtin.PRIV_VIEW_USER_SECRET))

  def get_udoc_setting(self, udoc, key):
    if self.can_view(udoc, key):
      return udoc.get(key, None)
    else:
      return None


@app.route('/register', 'user_register')
class UserRegisterHandler(base.Handler):
    @base.require_priv(builtin.PRIV_REGISTER_USER)
    async def get(self):
        self.render('user_register.html')

    @base.require_priv(builtin.PRIV_REGISTER_USER)
    @base.limit_rate('user_register', 3600, 60)
    @base.post_argument
    @base.sanitize
    async def post(self, *, mail: str):
        validator.check_mail(mail)
        if await user.get_by_mail(mail):
            raise error.UserAlreadyExistError(mail)
        rid, _ = await token.add(token.TYPE_REGISTRATION,
                                 options.options.registration_token_expire_seconds,
                                 mail=mail)
        await self.send_mail(mail, 'Sign Up', 'user_register_mail.html',
                             url=self.reverse_url('user_register_with_code', code=rid))
        self.render('user_register_mail_sent.html')


@app.route('/register/{code}', 'user_register_with_code')
class UserRegisterWithCodeHandler(base.Handler):
    TITLE = 'user_register'

    @base.require_priv(builtin.PRIV_REGISTER_USER)
    @base.route_argument
    @base.sanitize
    async def get(self, *, code: str):
        doc = await token.get(code, token.TYPE_REGISTRATION)
        if not doc:
            raise error.InvalidTokenError(token.TYPE_REGISTRATION, code)
        self.render('user_register_with_code.html', mail=doc['mail'])

    @base.require_priv(builtin.PRIV_REGISTER_USER)
    @base.route_argument
    @base.post_argument
    @base.sanitize
    async def post(self, *, code: str, uname: str, password: str, verify_password: str):
        validator.check_uname(uname)
        doc = await token.get(code, token.TYPE_REGISTRATION)
        if not doc:
            raise error.InvalidTokenError(token.TYPE_REGISTRATION, code)
        if re.fullmatch(r'^team\d+$', uname) or await user.get_by_uname(uname):
            raise error.UserAlreadyExistError(uname)
        if password != verify_password:
            raise error.VerifyPasswordError()
        uid = await user.add(uname, password, doc['mail'], self.remote_ip)
        await domain.set_user_role(builtin.DOMAIN_ID_SYSTEM, uid, builtin.ROLE_DEFAULT)
        await token.delete(code, token.TYPE_REGISTRATION)
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
        udoc = await user.check_password_by_uname(uname, password)
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


@app.route('/user/{uid:-?\d+}', 'user_detail')
class UserDetailHandler(base.Handler, UserSettingsMixin):
    @base.route_argument
    @base.sanitize
    async def get(self, *, uid: int):
        is_self_profile = self.has_priv(builtin.PRIV_USER_PROFILE) and self.user['_id'] == uid
        udoc = await user.get_by_uid(uid)
        if not udoc:
            raise error.UserNotFoundError(uid)
        dudoc = await domain.get_user(self.domain_id, udoc['_id'])
        email = self.get_udoc_setting(udoc, 'mail')
        if email:
            email = email.replace('@', random.choice([' [at] ', '#']))
        bg = random.randint(1, 21)
        rdocs = record.get_multi(get_hidden=self.has_priv(builtin.PRIV_VIEW_HIDDEN_RECORD),
                                 uid=uid).sort([('_id', -1)])
        rdocs = await rdocs.limit(10).to_list(None)
        # TODO(twd2): check status, eg. test, hidden problem, ...
        pdocs = problem.get_multi(domain_id=self.domain_id, owner_uid=uid).sort([('_id', -1)])
        pcount = await pdocs.count()
        pdocs = await pdocs.limit(10).to_list(None)
        ddocs = discussion.get_multi(self.domain_id, owner_uid=uid)
        dcount = await ddocs.count()
        ddocs = await ddocs.limit(10).to_list(None)
        self.render('user_detail.html', is_self_profile=is_self_profile,
                    udoc=udoc, dudoc=dudoc, email=email, bg=bg,
                    rdocs=rdocs, pdocs=pdocs, pcount=pcount,
                    ddocs=ddocs, dcount=dcount)


@app.route('/user/search', 'user_search')
class UserSearchHandler(base.Handler):
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.get_argument
    @base.route_argument
    @base.sanitize
    async def get(self, *, q: str):
        udocs = await user.get_prefix_list(q, user.PROJECTION_PUBLIC, 20)
        try:
            udoc = await user.get_by_uid(int(q), user.PROJECTION_PUBLIC)
            if udoc:
                udocs.insert(0, udoc)
        except ValueError as e:
            pass
        for udoc in udocs:
            if 'gravatar' in udoc:
                udoc['gravatar_url'] = template.gravatar_url(udoc.pop('gravatar'))
        self.json(udocs)
