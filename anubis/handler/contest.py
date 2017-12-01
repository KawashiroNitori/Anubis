import asyncio
import calendar
import datetime
import functools
import io
import pytz
import zipfile
from bson import objectid

from anubis import app
from anubis import constant
from anubis import error
from anubis.model import builtin
from anubis.model import opcount
from anubis.model import record
from anubis.model import user
from anubis.model import problem
from anubis.model import contest
from anubis.model import discussion
from anubis.handler import base
from anubis.util import pagination
from anubis.util import json
from anubis.util.orderedset import OrderedSet
from anubis.service import bus


class ContestStatusMixin(object):
    @property
    @functools.lru_cache()
    def now(self):
        # TODO: This does not work on multi-machine environment
        return datetime.datetime.utcnow()

    def is_new(self, tdoc):
        ready_at = tdoc['begin_at'] - datetime.timedelta(days=1)
        return self.now < ready_at

    def is_ready(self, tdoc):
        ready_at = tdoc['begin_at'] - datetime.timedelta(days=1)
        return ready_at <= self.now < tdoc['begin_at']

    def is_live(self, tdoc):
        return tdoc['begin_at'] <= self.now < tdoc['end_at']

    def is_done(self, tdoc):
        return tdoc['end_at'] <= self.now

    def status_text(self, tdoc):
        if self.is_new(tdoc):
            return 'New'
        elif self.is_ready(tdoc):
            return 'Ready (☆▽☆)'
        elif self.is_live(tdoc):
            return 'Live...'
        else:
            return 'Done'

    def can_show(self, tdoc):
        return contest.RULES[tdoc['rule']].show_func(tdoc, self.now)


@app.route('/contest', 'contest_main')
class ContestMainHandler(base.Handler, ContestStatusMixin):
    CONTESTS_PER_PAGE = 20

    @base.require_perm(builtin.PERM_VIEW_CONTEST)
    @base.get_argument
    @base.sanitize
    async def get(self, *, rule: str=None, page: int=1):
        if not rule:
            tdocs = contest.get_multi(self.domain_id)
            qs = ''
        else:
            tdocs = contest.get_multi(self.domain_id, rule=int(rule))
            qs = 'rule={0}'.format(int(rule))
        tdocs, tpcount, _ = await pagination.paginate(tdocs, page, self.CONTESTS_PER_PAGE)
        tsdict = await contest.get_dict_status(self.domain_id, self.user['_id'],
                                               (tdoc['_id'] for tdoc in tdocs))
        self.render('contest_main.html', page=page, tpcount=tpcount, qs=qs,
                    tdocs=tdocs, tsdict=tsdict)


@app.route('/contest/{tid:\d{4,}}', 'contest_detail')
class ContestDetailHandler(base.OperationHandler, ContestStatusMixin):
    DISCUSSIONS_PER_PAGE = 15

    @base.require_perm(builtin.PERM_VIEW_CONTEST)
    @base.get_argument
    @base.route_argument
    @base.sanitize
    async def get(self, *, tid: int, page: int=1):
        tdoc = await contest.get(self.domain_id, tid)
        tsdoc, pdict = await asyncio.gather(
            contest.get_status(self.domain_id, tdoc['_id'], self.user['_id']),
            problem.get_dict(self.domain_id, tdoc['pids'])
        )
        for index, pid in enumerate(tdoc['pids']):
            pdict[pid]['letter'] = chr(ord('A') + index)
        psdict = dict()
        rdict = dict()
        if tsdoc:
            attended = tsdoc.get('attend') == 1
            for pdetail in tsdoc.get('detail', []):
                psdict[pdetail['pid']] = pdetail
            rdict = await record.get_dict(psdoc['rid'] for psdoc in psdict.values())
        else:
            attended = False
        # discussion
        ddocs, dpcount, dcount = await pagination.paginate(
            discussion.get_multi(self.domain_id,
                                 parent_type='contest',
                                 parent_id=tdoc['_id']),
            page, self.DISCUSSIONS_PER_PAGE
        )
        uids = set(ddoc['owner_uid'] for ddoc in ddocs)
        uids.add(tdoc['owner_uid'])
        udict = await user.get_dict(uids)
        path_components = self.build_path(
            (self.translate('contest_main'), self.reverse_url('contest_main')),
            (tdoc['title'], None)
        )
        print(rdict)
        self.render('contest_detail.html', tdoc=tdoc, tsdoc=tsdoc, attended=attended, udict=udict,
                    pdict=pdict, psdict=psdict, rdict=rdict,
                    ddocs=ddocs, page=page, dpcount=dpcount, dcount=dcount,
                    datetime_stamp=self.datetime_stamp,
                    page_title=tdoc['title'], path_components=path_components)

    @base.require_perm(builtin.PERM_ATTEND_CONTEST)
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.route_argument
    @base.require_csrf_token
    @base.sanitize
    async def post_attend(self, *, tid: int):
        tdoc = await contest.get(self.domain_id, tid)
        if tdoc['private']:
            raise error.ContestIsPrivateError(tdoc['_id'])
        if self.is_done(tdoc):
            raise error.ContestNotLiveError(tdoc['_id'])
        await contest.attend(self.domain_id, tdoc['_id'], self.user['_id'])
        self.json_or_redirect(self.url)


@app.route('/contest/{tid:\d{4,}}/code', 'contest_code')
class ContestCodeHandler(base.OperationHandler):
    @base.require_perm(builtin.PERM_VIEW_CONTEST)
    @base.require_perm(builtin.PERM_READ_RECORD_CODE)
    @base.limit_rate('contest_code', 3600, 60)
    @base.route_argument
    @base.sanitize
    async def get(self, *, tid: int):
        tdoc, tsdocs = await contest.get_and_list_status(self.domain_id, tid)
        rnames = {}
        for tsdoc in tsdocs:
            udoc = await user.get_by_uid(tsdoc['uid'])
            for pdetail in tsdoc.get('detail', []):
                rnames[pdetail['rid']] = '{}/{}_{}'.format(contest.convert_to_letter(tdoc['pids'], pdetail['pid']),
                                                           udoc['uname'],
                                                           pdetail['rid'])
        output_buffer = io.BytesIO()
        zip_file = zipfile.ZipFile(output_buffer, 'w', zipfile.ZIP_DEFLATED)
        rdocs = record.get_multi(get_hidden=True, _id={'$in': list(rnames.keys())})
        async for rdoc in rdocs:
            zip_file.writestr('{}.{}'.format(rnames[rdoc['_id']], rdoc['lang']), rdoc['code'])
        for zfile in zip_file.filelist:
            zfile.create_system = 0
        zip_file.close()

        await self.binary(output_buffer.getvalue(),
                          'application/zip',
                          filename='{}_{}.zip'.format(tdoc['_id'], tdoc['title']))


@app.route('/contest/{tid:\d{4,}}/{letter:[A-Z]}', 'contest_detail_problem')
class ContestDetailProblemHandler(base.Handler, ContestStatusMixin):
    @base.require_perm(builtin.PERM_VIEW_CONTEST)
    @base.require_perm(builtin.PERM_VIEW_PROBLEM)
    @base.route_argument
    @base.sanitize
    async def get(self, *, tid: int, letter: str):
        uid = self.user['_id'] if self.has_priv(builtin.PRIV_USER_PROFILE) else None
        tdoc = await contest.get(self.domain_id, tid)
        pid = contest.convert_to_pid(tdoc['pids'], letter)
        pdoc = await problem.get(self.domain_id, pid, uid)
        if not pdoc:
            raise error.ProblemNotFoundError(self.domain_id, pid, tdoc['_id'])
        pdoc['letter'] = letter
        if not self.is_done(tdoc):
            tsdoc = await contest.get_status(self.domain_id, tdoc['_id'], self.user['_id'])
            if not tsdoc or tsdoc.get('attend') != 1:
                raise error.ContestNotAttendedError(tdoc['_id'])
            if not self.is_live(tdoc):
                raise error.ContestNotLiveError(tdoc['_id'])
        tsdoc, udoc = await asyncio.gather(
            contest.get_status(self.domain_id, tdoc['_id'], self.user['_id']),
            user.get_by_uid(tdoc['owner_uid']))
        attended = tsdoc and tsdoc.get('attend') == 1
        path_components = self.build_path(
            (self.translate('contest_main'), self.reverse_url('contest_main')),
            (tdoc['title'], self.reverse_url('contest_detail', tid=tid)),
            (pdoc['title'], None)
        )
        self.render('problem_detail.html', tdoc=tdoc, pdoc=pdoc, tsdoc=tsdoc, udoc=udoc,
                    attended=attended,
                    page_title=pdoc['title'], path_components=path_components)


@app.route('/contest/{tid:\d{4,}}/balloon', 'contest_balloon')
class ContestBalloonHandler(base.OperationHandler, ContestStatusMixin):
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_perm(builtin.PERM_SEND_CONTEST_BALLOON)
    @base.route_argument
    @base.sanitize
    async def get(self, *, tid: int):
        tdocs = await contest.get_multi(self.domain_id, **{'begin_at': {'$lte': self.now},
                                                           'end_at': {'$gt': self.now}}).to_list(None)
        tdocs_dict = {tdoc['_id']: tdoc for tdoc in tdocs}
        tids = [tdoc['_id'] for tdoc in tdocs]
        query = {'domain_id': self.domain_id,
                 'tid': {'$in': list(set(tids))},
                 'detail.accept': True,
                 'detail.balloon': False}
        tsdocs = await contest.get_multi_status(**query).sort('_id', 1).to_list(None)
        balloons = []
        for tsdoc in tsdocs:
            for pstatus in tsdoc['detail']:
                if pstatus['accept'] and not pstatus['balloon']:
                    balloons.append({'tid': tsdoc['tid'],
                                     'uid': tsdoc['uid'],
                                     'pid': pstatus['pid'],
                                     'balloon': pstatus['balloon']})
        udict, udoc, tdoc = await asyncio.gather(
            user.get_dict([balloon['uid'] for balloon in balloons]),
            user.get_by_uid(self.user['_id']),
            contest.get(self.domain_id, tid))
        for balloon in balloons:
            balloon.update({'uname': udict[balloon['uid']]['uname'],
                            'nickname': udict[balloon['uid']].get('nickname', ''),
                            'letter': contest.convert_to_letter(tdocs_dict[balloon['tid']]['pids'], balloon['pid'])})
        if not self.prefer_json:
            path_components = self.build_path(
                (self.translate('contest_main'), self.reverse_url('contest_main')),
                (tdoc['title'], self.reverse_url('contest_detail', tid=tid)),
                (self.translate('contest_balloon'), None)
            )
            self.render('contest_balloon.html', path_components=path_components,
                        udict=udict, udoc=udoc, tdoc=tdoc, balloons=balloons)
        else:
            self.json({'balloons': balloons})

    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_perm(builtin.PERM_SEND_CONTEST_BALLOON)
    @base.require_csrf_token
    @base.sanitize
    async def send_or_cancel(self, *, tid: int, uid: int, pid: int, balloon: bool=True):
        tsdoc = await contest.get_status(self.domain_id, tid, uid)
        pdetail = None
        for pstatus in tsdoc['detail']:
            if pstatus['pid'] == pid:
                pdetail = pstatus
                break
        if not pdetail:
            raise error.ProblemNotFoundError(self.domain_id, pid)
        if balloon and (not pdetail['accept'] or pdetail['balloon']):
            raise error.ContestIllegalBalloonError()
        await contest.set_status_balloon(self.domain_id, tid, uid, pid, balloon)
        self.json_or_redirect(self.reverse_url('contest_balloon', tid=tid))

    post_send = functools.partialmethod(send_or_cancel, balloon=True)
    post_cancel = functools.partialmethod(send_or_cancel, balloon=False)


@app.connection_route('/contest/balloon-conn', 'contest_balloon-conn')
class ContestBalloonConnection(base.Connection):
    @base.require_perm(builtin.PERM_SEND_CONTEST_BALLOON)
    async def on_open(self):
        bus.subscribe(self.on_message, ['balloon_change'])

    async def on_message(self, e):
        self.send(**json.decode(e['value']))

    async def on_close(self):
        bus.unsubscribe(self.on_message)
        

@app.connection_route('/contest/{tid:\d{4,}}/notification-conn', 'contest_notification-conn')
class ContestNotificationConnection(base.Connection, ContestStatusMixin):
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    async def on_open(self):
        await super(ContestNotificationConnection, self).on_open()
        tid = int(self.request.match_info['tid'])
        tdoc = await contest.get(self.domain_id, tid)
        if self.is_done(tdoc):
            raise error.ContestNotLiveError(tid)
        tsdoc = await contest.get_status(self.domain_id, tid, self.user['_id'])
        bus.subscribe(self.on_notification, ['contest_notification-' + str(tid)])

    async def on_notification(self, e):
        self.send(**json.decode(e['value']))

    async def on_close(self):
        bus.unsubscribe(self.on_notification)


@app.route('/contest/{tid:\d{4,}}/{letter:[A-Z]}/submit', 'contest_detail_problem_submit')
class ContestDetailProblemSubmitHandler(base.Handler, ContestStatusMixin):
    @base.require_perm(builtin.PERM_VIEW_CONTEST)
    @base.require_perm(builtin.PERM_SUBMIT_PROBLEM)
    @base.route_argument
    @base.sanitize
    async def get(self, *, tid: int, letter: str):
        uid = self.user['_id'] if self.has_priv(builtin.PRIV_USER_PROFILE) else None
        tdoc = await contest.get(self.domain_id, tid)
        pid = contest.convert_to_pid(tdoc['pids'], letter)
        pdoc = await problem.get(self.domain_id, pid, uid)
        if not pdoc:
            raise error.ProblemNotFoundError(self.domain_id, pid, tdoc['_id'])
        pdoc['letter'] = letter
        tsdoc, udoc = await asyncio.gather(
            contest.get_status(self.domain_id, tdoc['_id'], self.user['_id']),
            user.get_by_uid(tdoc['owner_uid'])
        )
        attended = tsdoc and tsdoc.get('attend') == 1
        if (contest.RULES[tdoc['rule']].show_func(tdoc, self.now)
                or self.has_perm(builtin.PERM_VIEW_CONTEST_HIDDEN_STATUS)):
            rdocs = await record.get_user_in_problem_multi(
                uid, self.domain_id, pdoc['_id']).sort([('_id', -1)]).to_list(10)
        else:
            rdocs = []
        if not self.prefer_json:
            path_components = self.build_path(
                (self.translate('contest_main'), self.reverse_url('contest_main')),
                (tdoc['title'], self.reverse_url('contest_detail', tid=tid)),
                (pdoc['title'], self.reverse_url('contest_detail_problem', tid=tid, letter=pdoc['letter'])),
                (self.translate('contest_detail_problem_submit'), None)
            )
            self.render('problem_submit.html', tdoc=tdoc, pdoc=pdoc, rdocs=rdocs,
                        tsdoc=tsdoc, udoc=udoc, attended=attended,
                        page_title=pdoc['title'], path_components=path_components)
        else:
            self.json({'rdocs': rdocs})

    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_perm(builtin.PERM_VIEW_CONTEST)
    @base.require_perm(builtin.PERM_SUBMIT_PROBLEM)
    @base.route_argument
    @base.post_argument
    @base.require_csrf_token
    @base.sanitize
    async def post(self, *, tid: int, letter: str, lang: str, code: str):
        tdoc = await contest.get(self.domain_id, tid)
        pid = contest.convert_to_pid(tdoc['pids'], letter)
        pdoc = await problem.get(self.domain_id, pid)
        tsdoc = await contest.get_status(self.domain_id, tdoc['_id'], self.user['_id'])
        if not tsdoc or tsdoc.get('attend') != 1:
            raise error.ContestNotAttendedError(tdoc['_id'])
        if not self.is_live(tdoc):
            raise error.ContestNotLiveError(tdoc['_id'])
        if not pdoc:
            raise error.ProblemNotFoundError(self.domain_id, pid, tdoc['_id'])
        rid = await record.add(self.domain_id, pdoc['_id'], constant.record.TYPE_SUBMISSION,
                               self.user['_id'], lang, code, tid=tdoc['_id'], hidden=True)
        # here is a update status.
        # await contest.update_status(self.domain_id, tdoc['_id'], self.user['_id'],
        #                             rid, pdoc['_id'], False, 0)
        if (not contest.RULES[tdoc['rule']].show_func(tdoc, self.now)
                and not self.has_perm(builtin.PERM_VIEW_CONTEST_HIDDEN_STATUS)):
            self.json_or_redirect(self.reverse_url('contest_detail', tid=tdoc['_id']))
        else:
            self.json_or_redirect(self.reverse_url('record_detail', rid=rid))


@app.route('/contest/{tid:\d{4,}}/status', 'contest_status')
class ContestStatusHandler(base.Handler, ContestStatusMixin):
    @base.require_perm(builtin.PERM_VIEW_CONTEST)
    @base.require_perm(builtin.PERM_VIEW_CONTEST_STATUS)
    @base.route_argument
    @base.sanitize
    async def get(self, *, tid: int):
        tdoc, tsdocs = await contest.get_and_list_status(self.domain_id, tid)
        if (not contest.RULES[tdoc['rule']].show_func(tdoc, self.now)
                and not self.has_perm(builtin.PERM_VIEW_CONTEST_HIDDEN_STATUS)):
            raise error.ContestStatusHiddenError()
        udict, pdict = await asyncio.gather(
            user.get_dict([tsdoc['uid'] for tsdoc in tsdocs]),
            problem.get_dict(self.domain_id, tdoc['pids'])
        )
        for index, pid in enumerate(tdoc['pids']):
            pdict[pid]['letter'] = chr(ord('A') + index)
        ranked_tsdocs = contest.RULES[tdoc['rule']].rank_func(tsdocs)
        path_components = self.build_path(
            (self.translate('contest_main'), self.reverse_url('contest_main')),
            (tdoc['title'], self.reverse_url('contest_detail', tid=tdoc['_id'])),
            (self.translate('contest_status'), None)
        )
        self.render('contest_status.html', tdoc=tdoc, ranked_tsdocs=ranked_tsdocs, dict=dict,
                    udict=udict, pdict=pdict, path_components=path_components)


@app.route('/contest/{tid:\d{4,}}/edit', 'contest_edit')
class ContestEditHandler(base.Handler, ContestStatusMixin):
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.route_argument
    @base.sanitize
    async def get(self, *, tid: int):
        tdoc = await contest.get(self.domain_id, tid)
        if not self.own(tdoc, builtin.PERM_EDIT_CONTEST_SELF):
            self.check_perm(builtin.PERM_EDIT_CONTEST)
        udoc = await user.get_by_uid(self.user['_id'])
        tsdoc = await contest.get_status(self.domain_id, tid, self.user['_id'])
        attended = tsdoc and tsdoc.get('attend') == 1
        duration = (tdoc['end_at'] - tdoc['begin_at']).total_seconds() / 3600  # Seconds to hours
        pids = ','.join(list(map(str, tdoc['pids'])))
        path_components = self.build_path(
            (self.translate('contest_main'), self.reverse_url('contest_main')),
            (tdoc['title'], self.reverse_url('contest_detail', tid=tdoc['_id'])),
            (self.translate('contest_edit'), None))
        self.render('contest_edit.html', tdoc=tdoc, udoc=udoc,
                    duration=duration, pids=pids, attended=attended,
                    date_text=tdoc['begin_at'].strftime('%Y-%m-%d'),
                    time_text=tdoc['begin_at'].strftime('%H:%M'),
                    page_title=tdoc['title'], path_components=path_components)

    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_perm(builtin.PERM_EDIT_PROBLEM)
    @base.route_argument
    @base.post_argument
    @base.require_csrf_token
    @base.sanitize
    async def post(self, *, tid: int, title: str, content: str, rule: int, private: bool=False,
                   begin_at_date: str, begin_at_time: str,
                   duration: float, pids: str):
        tdoc = await contest.get(self.domain_id, tid)
        if not self.own(tdoc, builtin.PERM_EDIT_CONTEST_SELF):
            self.check_perm(builtin.PERM_EDIT_CONTEST)
        try:
            begin_at = datetime.datetime.strptime(begin_at_date + ' ' + begin_at_time, '%Y-%m-%d %H:%M')
            begin_at = self.timezone.localize(begin_at).astimezone(pytz.utc).replace(tzinfo=None)
            end_at = begin_at + datetime.timedelta(hours=duration)
        except ValueError:
            raise error.ValidationError('begin_at_date', 'begin_at_time')
        if begin_at >= end_at:
            raise error.ValidationError('duration')
        pids = list(OrderedSet(map(int, pids.split(','))))
        pdocs = await problem.get_multi(domain_id=self.domain_id, _id={'$in': pids},
                                        projection={'_id': 1}).sort('_id', 1).to_list(None)
        exist_pids = [pdoc['_id'] for pdoc in pdocs]
        if len(pids) != len(exist_pids):
            for pid in pids:
                if pid not in exist_pids:
                    raise error.ProblemNotFoundError(self.domain_id, pid)
        await contest.edit(domain_id=self.domain_id, tid=tid,
                           title=title, content=content, rule=rule, private=private,
                           begin_at=begin_at, end_at=end_at, pids=pids)
        for pid in pids:
            await problem.set_hidden(self.domain_id, pid, True)
        self.json_or_redirect(self.reverse_url('contest_detail', tid=tid))


@app.route('/contest/create', 'contest_create')
class ContestCreateHandler(base.Handler, ContestStatusMixin):
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_perm(builtin.PERM_CREATE_CONTEST)
    async def get(self):
        dt = self.now.replace(tzinfo=pytz.utc).astimezone(self.timezone)
        ts = calendar.timegm(dt.utctimetuple())
        # find next quarter
        ts = ts - ts % (15 * 60) + 15 * 60
        dt = datetime.datetime.fromtimestamp(ts, self.timezone)
        self.render('contest_edit.html',
                    date_text=dt.strftime('%Y-%m-%d'),
                    time_text=dt.strftime('%H:%M'))

    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_perm(builtin.PERM_EDIT_PROBLEM)
    @base.require_perm(builtin.PERM_CREATE_CONTEST)
    @base.post_argument
    @base.require_csrf_token
    @base.sanitize
    async def post(self, *, title: str, content: str, rule: int, private: bool=False,
                   begin_at_date: str,
                   begin_at_time: str,
                   duration: float,
                   pids: str):
        try:
            begin_at = datetime.datetime.strptime(begin_at_date + ' ' + begin_at_time, '%Y-%m-%d %H:%M')
            begin_at = self.timezone.localize(begin_at).astimezone(pytz.utc).replace(tzinfo=None)
            end_at = begin_at + datetime.timedelta(hours=duration)
        except ValueError:
            raise error.ValidationError('begin_at_date', 'begin_at_time')
        if begin_at <= self.now:
            raise error.ValidationError('begin_at_date', 'begin_at_time')
        if begin_at >= end_at:
            raise error.ValidationError('duration')
        pids = list(OrderedSet(map(int, pids.split(','))))
        pdocs = await problem.get_multi(domain_id=self.domain_id, _id={'$in': pids},
                                        projection={'_id': 1}).sort('_id', 1).to_list(None)
        exist_pids = [pdoc['_id'] for pdoc in pdocs]
        if len(pids) != len(exist_pids):
            for pid in pids:
                if pid not in exist_pids:
                    raise error.ProblemNotFoundError(self.domain_id, pid)
        tid = await contest.add(self.domain_id, title, content, self.user['_id'],
                                rule, private, begin_at, end_at, pids)
        for pid in pids:
            await problem.set_hidden(self.domain_id, pid, True)
        self.json_or_redirect(self.reverse_url('contest_detail', tid=tid))
