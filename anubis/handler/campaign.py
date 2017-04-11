import io
import csv
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
from anubis.model import discussion
from anubis.handler import base
from anubis.util import pagination
from anubis.util import validator
from anubis.service import gen_pdf


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
        return self.now < cdoc['begin_at']


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
    DISCUSSIONS_PER_PAGE = 15

    @base.require_perm(builtin.PERM_VIEW_CAMPAIGN)
    @base.route_argument
    @base.get_argument
    @base.sanitize
    async def get(self, *, cid: str, page: int=1):
        cdoc = await campaign.get(cid)
        # discussion
        ddocs, dpcount, dcount = await pagination.paginate(
            discussion.get_multi(builtin.DOMAIN_ID_SYSTEM,
                                 parent_type='campaign',
                                 parent_id=cdoc['_id']),
            page, self.DISCUSSIONS_PER_PAGE
        )
        team = await campaign.get_team_by_uid(cid, self.user['_id'])
        attended = bool(team)
        uids = set(ddoc['owner_uid'] for ddoc in ddocs)
        uids.add(cdoc['owner_uid'])
        udict = await user.get_dict(uids)
        path_components = self.build_path(
            (self.translate('campaign_main'), self.reverse_url('campaign_main')),
            (cdoc['title'], None)
        )
        self.render('campaign_detail.html', path_components=path_components, udoc=self.user,
                    cdoc=cdoc, page_title=cdoc['title'], udict=udict, attended=attended,
                    ddocs=ddocs, page=page, dpcount=dpcount, dcount=dcount,
                    datetime_stamp=self.datetime_stamp)


@app.route('/campaign/{cid}/attend', 'campaign_attend')
class CampaignAttendHandler(base.Handler, CampaignStatusMixin):
    @base.require_priv(builtin.PRIV_USER_PROFILE | builtin.PRIV_ATTEND_CAMPAIGN)
    @base.route_argument
    @base.sanitize
    async def get(self, *, cid: str):
        cdoc = await campaign.get(cid)
        if not self.is_live(cdoc):
            raise error.CampaignNotInTimeError(cdoc['title'])
        team = await campaign.get_team_by_uid(cid, self.user['_id'])
        attended = bool(team)
        if not attended:
            page_title = self.translate('campaign_attend')
        else:
            page_title = self.translate('Edit Attend Information')
        if team:
            team['members'] = await student.get_list(team['members'])
        else:
            team = {'mail': self.user['mail'], 'tel': '', 'team_name': '', 'members': []}
        path_components = self.build_path(
            (self.translate('campaign_main'), self.reverse_url('campaign_main')),
            (cdoc['title'], self.reverse_url('campaign_detail', cid=cdoc['_id'])),
            (page_title, None)
        )
        if not self.prefer_json or not team:
            self.render('campaign_attend.html', page_title=page_title,
                        path_components=path_components, cdoc=cdoc, udoc=self.user, team=team,
                        attended=attended)
        else:
            self.json(team)

    @base.require_priv(builtin.PRIV_USER_PROFILE | builtin.PRIV_ATTEND_CAMPAIGN)
    @base.route_argument
    @base.post_argument
    @base.require_csrf_token
    @base.sanitize
    async def post(self, *, cid: str, mail: str, tel: str, team_name: str, is_newbie: bool=False,
                   member_id: str, member_id_number: str):
        validator.check_mail(mail)
        validator.check_tel(tel)
        validator.check_team_name(team_name)
        members = list(zip(self.request.POST.getall('member_id'),
                           self.request.POST.getall('member_id_number')))
        if len(members) > 3 or len(members) < 1:
            raise error.ValidationError('members')
        cdoc = await campaign.get(cid)
        if not cdoc['is_newbie'] and is_newbie:
            raise error.ValidationError('is_newbie')
        if not self.is_live(cdoc):
            raise error.CampaignNotInTimeError(cdoc['title'])

        for member in members:
            sdoc = await student.check_student_by_id(*member)
            if is_newbie and sdoc['grade'] != datetime.datetime.utcnow().year:
                raise error.StudentIsNotNewbieError(member[0])
        members = [member[0] for member in members]
        await campaign.attend(cid, self.user['_id'], mail, tel, team_name, is_newbie, members)
        redirect_url = self.reverse_url('campaign_teams', cid=cid)
        self.json_or_redirect(redirect_url, redirect=redirect_url)


@app.route('/campaign/{cid}/edit', 'campaign_edit')
class CampaignEditHandler(base.Handler, CampaignStatusMixin):
    @base.require_priv(builtin.PRIV_USER_PROFILE | builtin.PRIV_EDIT_CAMPAIGN)
    @base.route_argument
    @base.sanitize
    async def get(self, *, cid: str):
        uid = self.user['_id']
        cdoc = await campaign.get(cid)
        udoc = await user.get_by_uid(cdoc['owner_uid'])
        dt = cdoc['begin_at'].replace(tzinfo=pytz.utc).astimezone(self.timezone)
        end_dt = cdoc['end_at'].replace(tzinfo=pytz.utc).astimezone(self.timezone)
        path_components = self.build_path(
            (self.translate('campaign_main'), self.reverse_url('campaign_main')),
            (cdoc['title'], self.reverse_url('campaign_detail', cid=cid)),
            (self.translate('campaign_edit'), None)
        )
        self.render('campaign_edit.html', cdoc=cdoc, udoc=udoc, page_title=cdoc['title'],
                    path_components=path_components,
                    begin_date_text=dt.strftime('%Y-%m-%d'), begin_time_text=dt.strftime('%H:%M'),
                    end_date_text=end_dt.strftime('%Y-%m-%d'),
                    end_time_text=end_dt.strftime('%H:%M'))

    @base.require_priv(builtin.PRIV_USER_PROFILE | builtin.PRIV_EDIT_CAMPAIGN)
    @base.post_argument
    @base.route_argument
    @base.require_csrf_token
    @base.sanitize
    async def post(self, *, cid: str, title: str, content: str,
                   begin_at_date: str, begin_at_time: str,
                   end_at_date: str, end_at_time: str,
                   is_newbie: bool=False):
        try:
            begin_at = datetime.datetime.strptime(begin_at_date + ' ' + begin_at_time, '%Y-%m-%d %H:%M')
            begin_at = self.timezone.localize(begin_at).astimezone(pytz.utc).replace(tzinfo=None)
            end_at = datetime.datetime.strptime(end_at_date + ' ' + end_at_time, '%Y-%m-%d %H:%M')
            end_at = self.timezone.localize(end_at).astimezone(pytz.utc).replace(tzinfo=None)
        except ValueError:
            raise error.ValidationError('begin_at_date', 'begin_at_time')
        if begin_at >= end_at:
            raise error.ValidationError('begin_at_date', 'begin_at_time')
        await campaign.edit(cid, title=title, content=content,
                            begin_at=begin_at, end_at=end_at, is_newbie=is_newbie)
        self.json_or_redirect(self.reverse_url('campaign_detail', cid=cid))


@app.route('/campaign/{cid}/teams', 'campaign_teams')
class CampaignManageHandler(base.OperationHandler, CampaignStatusMixin):
    @base.route_argument
    @base.sanitize
    async def get(self, *, cid: str):
        cdoc = await campaign.get(cid)
        teams = await campaign.get_list_team(cid)
        students = []
        sdict = {}
        for team in teams:
            students += team['members']
        for sdoc in await student.get_list(students):
            sdict[sdoc['_id']] = sdoc
            sdict[sdoc['_id']]['id_number'] = sdoc['id_number'][-6:]
        attended = bool(await campaign.get_team_by_uid(cid, self.user['_id']))
        admin = self.has_priv(builtin.PRIV_CREATE_CAMPAIGN)

        if self.prefer_json:
            self.json({'teams': teams})
        else:
            path_components = self.build_path(
                (self.translate('campaign_main'), self.reverse_url('campaign_main')),
                (cdoc['title'], self.reverse_url('campaign_detail', cid=cid)),
                (self.translate('campaign_teams'), None)
            )
            self.render('campaign_teams.html', page_title=self.translate('campaign_teams'), cdoc=cdoc, admin=admin,
                        sdict=sdict, udoc=self.user, teams=teams, attended=attended, path_components=path_components)

    @base.require_priv(builtin.PRIV_USER_PROFILE | builtin.PRIV_CREATE_CAMPAIGN)
    @base.route_argument
    @base.sanitize
    @base.require_csrf_token
    async def post_update_user(self, *, cid: str, team_id: objectid.ObjectId, team_num: int):
        team_ids = [objectid.ObjectId(team_id) for team_id in self.request.POST.getall('team_id')]
        team_nums = self.request.POST.getall('team_num')
        teams = await campaign.get_multi_team(_id={'$in': list(set(team_ids))}).to_list(None)
        team_tuples = list(zip(['team{0}'.format(i) for i in team_nums], teams))
        await campaign.update_user_for_teams(team_tuples)
        self.json_or_redirect(self.reverse_url('campaign_teams', cid=cid))

    @base.require_priv(builtin.PRIV_USER_PROFILE | builtin.PRIV_CREATE_CAMPAIGN)
    @base.route_argument
    @base.sanitize
    @base.require_csrf_token
    async def post_attend_team(self, *, cid: str, domain_id: str, tid: int, team_num: int):
        team_nums = self.request.POST.getall('team_num')
        await campaign.attend_contest_for_teams(['team{0}'.format(num) for num in team_nums],
                                                domain_id, tid)
        self.json_or_redirect(self.reverse_url('campaign_teams', cid=cid))


@app.route('/campaign/{cid}/password', 'campaign_team_password')
class CampaignTeamPasswordHandler(base.Handler):
    @base.require_priv(builtin.PRIV_USER_PROFILE | builtin.PRIV_CREATE_CAMPAIGN)
    @base.route_argument
    @base.sanitize
    async def get(self, *, cid: str):
        teams = await campaign.get_list_team(cid)
        team_unames = ['team{0}'.format(i) for i in range(1, len(teams) + 1)]
        udocs = await user.get_multi(uname={'$in': team_unames}, fields={'uname': 1,
                                                                         'plain_pass': 1,
                                                                         'nickname': 1}).to_list(None)
        output_buffer = io.StringIO()
        reader = csv.writer(output_buffer)
        for index, udoc in enumerate(udocs):
            reader.writerow([udoc['uname'], teams[index]['team_name'], udoc['plain_pass']])

        await self.binary(b'\xef\xbb\xbf' + output_buffer.getvalue().encode('utf8'), 'application/csv',
                          filename='password_{0}.csv'.format(cid))


@app.route('/campaign/{cid}/card', 'campaign_team_card')
class CampaignTeamCardHandler(base.Handler):
    @base.route_argument
    @base.sanitize
    async def get(self, *, cid: str):
        teams = await campaign.get_list_team(cid)
        buf = gen_pdf.gen_team_pdf(list(enumerate(teams, 1))
        await self.binary(buf, 'application/pdf', filename='cards_{0}.pdf'.format(cid))


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

