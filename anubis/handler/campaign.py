import asyncio
import functools
import pytz
import datetime
import calendar
from bson import objectid

from anubis import app
from anubis import constant
from anubis import error
from anubis.model import builtin
from anubis.model import campaign
from anubis.model import user
from anubis.model import student
from anubis.handler import base
from anubis.util import pagination
from anubis.util import validator


class CampaignStatusMixin(object):
    @property
    @functools.lru_cache()
    def now(self):
        return datetime.datetime.utcnow()

    def is_live(self, cdoc):
        return cdoc['begin_at'] <= self.now < cdoc['end_at']

    def is_done(self, cdoc):
        return cdoc['end_at'] <= self.now

    def is_ready(self, cdoc):
        return self.now < cdoc['end_at']


@app.route('/campaign', 'campaign_main')
class CampaignMainHandler(base.Handler, CampaignStatusMixin):
    CAMPAIGNS_PER_PAGE = 20

    @base.require_perm(builtin.PERM_VIEW_CAMPAIGN)
    @base.get_argument
    @base.sanitize
    async def get(self, *, page: int=1):
        cdocs = campaign.get_multi()
        cdocs, cpcount, _ = await pagination.paginate(cdocs, page, self.CAMPAIGNS_PER_PAGE)
        self.render('campaign_main.html', page=page, cpcount=cpcount, cdocs=cdocs)


@app.route('/campaign/{cid:\w{7,}}', 'campaign_detail')
class CampaignDetailHandler(base.Handler, CampaignStatusMixin):
    @base.require_perm(builtin.PERM_VIEW_CAMPAIGN)
    @base.route_argument
    @base.sanitize
    async def get(self, *, cid: str):
        cdoc = await campaign.get(cid)
        path_components = self.build_path(
            (self.translate('campaign_main'), self.reverse_url('campaign_main')),
            (cdoc['title'], None)
        )
        self.render('campaign_detail.html', path_components=path_components, cdoc=cdoc, page_title=cdoc['title'])


@app.route('/campaign/{cid}/attend', 'campaign_attend')
class CampaignAttendHandler(base.Handler, CampaignStatusMixin):
    @base.require_priv(builtin.PRIV_USER_PROFILE | builtin.PRIV_ATTEND_CAMPAIGN)
    @base.route_argument
    @base.sanitize
    async def get(self, *, cid: str):
        cdoc = await campaign.get(cid)
        if not self.is_live(cdoc):
            raise error.CampaignNotInTimeError(cdoc['title'])
        path_components = self.build_path(
            (self.translate('campaign_main'), self.reverse_url('campaign_main')),
            (cdoc['title'], self.reverse_url('campaign_detail', cid=cdoc['_id'])),
            (self.translate('campaign_attend'), None)
        )
        self.render('campaign_attend.html', page_title=self.translate('campaign_attend'),
                    path_components=path_components, cdoc=cdoc, udoc=self.user)

    @base.require_priv(builtin.PRIV_USER_PROFILE | builtin.PRIV_ATTEND_CAMPAIGN)
    @base.route_argument
    @base.post_argument
    @base.require_csrf_token
    @base.sanitize
    async def post(self, *, cid: str, mail: str, tel: str, team_name: str,
                   member_id: str, member_id_number: str):
        validator.check_mail(mail)
        validator.check_tel(tel)
        validator.check_team_name(team_name)
        members = list(zip(self.request.POST.getall['member_id'],
                           self.request.POST.getall['member_id_number']))
        if len(members) > 3 or len(members) < 1:
            raise error.ValidationError('members')

        cdoc = await campaign.get(cid)
        if not self.is_live(cdoc):
            raise error.CampaignNotInTimeError(cdoc['title'])
        for member in members:
            await student.check_student_by_id(*member)
        members = [member[0] for member in members]
        await campaign.attend(cid, self.user['_id'], mail, tel, team_name, members)
        self.json_or_redirect(self.reverse_url('campaign_detail', cid=cid))


@app.route('/campaign/{cid}/edit', 'campaign_edit')
class CampaignEditHandler(base.Handler, CampaignStatusMixin):
    @base.require_priv(builtin.PRIV_USER_PROFILE | builtin.PRIV_EDIT_CAMPAIGN)
    @base.route_argument
    @base.sanitize
    async def get(self, *, cid: str):
        uid = self.user['_id']
        cdoc = await campaign.get(cid)
        udoc = await user.get_by_uid(cdoc['owner_uid'])
        dt = cdoc['begin_at']
        end_dt = cdoc['end_at']
        path_components = self.build_path(
            (self.translate('campaign_main'), self.reverse_url('campaign_main')),
            (cdoc['title'], self.reverse_url('campaign_detail', cid=cid)),
            (self.translate('campaign_edit'), None)
        )
        self.render('campaign_edit.html', cdoc=cdoc, owner_udoc=udoc, page_title=cdoc['title'],
                    path_components=path_components,
                    begin_date_text=dt.strftime('%Y-%m-%d'), begin_time_text=dt.strftime('%H:%M'),
                    end_date_text=end_dt.strftime('%Y-%m-%d'),
                    end_time_text=end_dt.strftime('%H:%M'))

    @base.require_priv(builtin.PRIV_USER_PROFILE | builtin.PRIV_EDIT_CAMPAIGN)
    @base.post_argument
    @base.route_argument
    @base.require_csrf_token
    @base.sanitize
    async def post(self, *, cid: str, campaign_id: str, title: str, content: str,
                   begin_at_date: str, begin_at_time: str,
                   end_at_date: str, end_at_time: str,
                   is_newbie: bool):
        try:
            begin_at = datetime.datetime.strptime(begin_at_date + ' ' + begin_at_time, '%Y-%m-%d %H:%M')
            begin_at = self.timezone.localize(begin_at).astimezone(pytz.utc).replace(tzinfo=None)
            end_at = datetime.datetime.strptime(end_at_date + ' ' + end_at_time, '%Y-%m-%d %H:%M')
            end_at = self.timezone.localize(end_at).astimezone(pytz.utc).replace(tzinfo=None)
        except ValueError:
            raise error.ValidationError('begin_at_date', 'begin_at_time')
        if begin_at >= end_at:
            raise error.ValidationError('begin_at_date', 'begin_at_time')
        await campaign.edit(campaign_id, title=title, content=content,
                            begin_at=begin_at, end_at=end_at, is_newbie=is_newbie)
        self.json_or_redirect(self.reverse_url('campaign_detail', cid=cid))


@app.route('/campaign/create', 'campaign_create')
class CampaignCreateHandler(base.Handler, CampaignStatusMixin):
    @base.require_priv(builtin.PRIV_USER_PROFILE | builtin.PRIV_CREATE_CAMPAIGN)
    async def get(self):
        dt = self.now.replace(tzinfo=pytz.utc).astimezone(self.timezone)
        ts = calendar.timegm(dt.utctimetuple())
        # find next quarter
        ts = ts - ts % (15 * 60) + 15 * 60
        dt = datetime.datetime.fromtimestamp(ts, self.timezone)
        end_dt = dt + datetime.timedelta(days=1)
        path_components = self.build_path(
            (self.translate('campaign_main'), self.reverse_url('campaign_main')),
            (self.translate('campaign_create'), None)
        )
        self.render('campaign_edit.html', begin_date_text=dt.strftime('%Y-%m-%d'),
                    page_title=self.translate('campaign_create'),
                    end_date_text=end_dt.strftime('%Y-%m-%d'),
                    end_time_text=end_dt.strftime('%H:%M'),
                    begin_time_text=dt.strftime('%H:%M'), path_components=path_components)

    @base.require_priv(builtin.PRIV_USER_PROFILE | builtin.PRIV_CREATE_CAMPAIGN)
    @base.post_argument
    @base.require_csrf_token
    @base.sanitize
    async def post(self, *, campaign_id: str, title: str, content: str,
                   begin_at_date: str, begin_at_time: str,
                   end_at_date: str, end_at_time: str,
                   is_newbie: bool=False):
        validator.check_campaign_id(campaign_id)
        validator.check_title(title)
        validator.check_content(content)
        try:
            begin_at = datetime.datetime.strptime(begin_at_date + ' ' + begin_at_time, '%Y-%m-%d %H:%M')
            begin_at = self.timezone.localize(begin_at).astimezone(pytz.utc).replace(tzinfo=None)
            end_at = datetime.datetime.strptime(end_at_date + ' ' + end_at_time, '%Y-%m-%d %H:%M')
            end_at = self.timezone.localize(end_at).astimezone(pytz.utc).replace(tzinfo=None)
        except ValueError:
            raise error.ValidationError('begin_at_date', 'begin_at_time')
        if begin_at <= self.now or begin_at >= end_at:
            raise error.ValidationError('begin_at_date', 'begin_at_time')
        cid = await campaign.add(campaign_id, title, content, self.user['_id'], begin_at, end_at, is_newbie)
        self.json_or_redirect(self.reverse_url('campaign_detail', cid=cid))

