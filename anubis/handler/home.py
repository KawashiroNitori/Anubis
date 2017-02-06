import asyncio
import hmac
import itertools

from bson import objectid

from anubis import app
from anubis import error
from anubis import template
from anubis.model import builtin
from anubis.model import domain
from anubis.model import token
from anubis.model import user
from anubis.model.adaptor import setting
from anubis.handler import base
from anubis.service import bus
from anubis.util import useragent
from anubis.util import geoip
from anubis.util import options
from anubis.util import validator


TOKEN_TYPE_TEXTS = {
    token.TYPE_SAVED_SESSION: 'Saved session',
    token.TYPE_UNSAVED_SESSION: 'Temporary session',
}


@app.route('/home/security', 'home_security')
class HomeSecurityHandler(base.OperationHandler):
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    async def get(self):
        # TODO: need pagination
        session = {
            'update_ip': self.session['update_ip'],
            'update_ua': useragent.parse(self.session['update_ua']),
            'update_geoip': geoip.ip2geo(self.session['update_ip'], self.get_setting('view_lang')),
            'update_at': self.session['update_at'],
            'token_type': self.session['token_type'],
            'token_digest': hmac.new(b'token_digest', str(self.session['_id']).encode(), 'sha256').hexdigest(),
        }
        self.render('home_security.html', session=session)

    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_csrf_token
    @base.sanitize
    async def post_change_password(self, *,
                                   current_password: str,
                                   new_password: str,
                                   verify_password: str):
        if new_password != verify_password:
            raise error.VerifyPasswordError()
        doc = await user.change_password(self.user['_id'], current_password, new_password)
        if not doc:
            raise error.CurrentPasswordError(self.user['_id'])
        self.json_or_redirect(self.url)

    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_csrf_token
    @base.sanitize
    async def post_change_mail(self, *, current_password: str, mail: str):
        validator.check_mail(mail)
        udoc, mail_holder_udoc = await asyncio.gather(
            user.check_password_by_uid(self.user['_id'], current_password),
            user.get_by_mail(mail)
        )
        # TODO: raise other errors.
        if not udoc:
            raise error.CurrentPasswordError(self.user['uname'])
        if mail_holder_udoc:
            raise error.UserAlreadyExistError(mail)
        rid, _ = await token.add(token.TYPE_CHANGEMAIL,
                                 options.options.changemail_token_expire_seconds,
                                 uid=udoc['_id'], mail=mail)
        await self.send_mail(mail, 'Change Email', 'user_changemail_mail.html',
                             url=self.reverse_url('user_changemail_with_code', code=rid),
                             uname=udoc['uname'])
        self.render('user_changemail_mail_send.html')


@app.route('/home/security/changemail/{code}', 'user_changemail_with_code')
class UserChangemailWithCodeHandler(base.Handler):
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.route_argument
    @base.sanitize
    async def get(self, *, code: str):
        tdoc = await token.get(code, token.TYPE_CHANGEMAIL)
        if not tdoc or tdoc['uid'] != self.user['_id']:
            raise error.InvalidTokenError(token.TYPE_CHANGEMAIL, code)
        mail_holder_udoc = await user.get_by_mail(tdoc['mail'])
        if mail_holder_udoc:
            raise error.UserAlreadyExistError(tdoc['mail'])
        # TODO: Ensure mail is unique
        await user.set_mail(self.user['_id'], tdoc['mail'])
        await token.delete(code, token.TYPE_CHANGEMAIL)
        self.json_or_redirect(self.reverse_url('home_security'))


@app.route('/home/account', 'home_account')
class HomeAccountHandler(base.Handler):
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    async def get(self):
        self.render('home_settings.html', category='account', settings=setting.ACCOUNT_SETTINGS)

    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.post_argument
    @base.require_csrf_token
    async def post(self, **kwargs):
        # TODO: check parameters
        await self.set_settings(**kwargs)
        self.json_or_redirect(self.url)


@app.route('/home/preference', 'home_preference')
class HomeAccountHandler(base.Handler):
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    async def get(self):
        self.render('home_settings.html', category='preference', settings=setting.PREFERENCE_SETTINGS)

    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.post_argument
    @base.require_csrf_token
    async def post(self, **kwargs):
        # TODO: check parameters
        await self.set_settings(**kwargs)
        self.json_or_redirect(self.url)


@app.route('/home/domain', 'home_domain')
class HomeDomainHandler(base.Handler):
    async def get(self):
        uddict = await domain.get_dict_user_by_domain_id(self.user['_id'])
        dids = list(uddict.keys())
        ddocs = await domain.get_multi(**{'$or': [{'_id': {'$in': dids}},
                                                  {'owner_uid': self.user['_id']}]}).to_list(None)
        self.render('home_domain.html', ddocs=ddocs, uddict=uddict)


@app.route('/home/domain/create', 'home_domain_create')
class HomeDomainCreateHandler(base.Handler):
    @base.require_priv(builtin.PRIV_CREATE_DOMAIN)
    async def get(self):
        self.render('home_domain_create.html')

    @base.require_priv(builtin.PRIV_CREATE_DOMAIN)
    @base.post_argument
    @base.require_csrf_token
    @base.sanitize
    async def post(self, *, id: str, name: str, gravatar: str):
        domain_id = await domain.add(id, self.user['_id'], name=name, gravatar=gravatar)
        self.json_or_redirect(self.reverse_url('domain_main', domain_id=domain_id))
