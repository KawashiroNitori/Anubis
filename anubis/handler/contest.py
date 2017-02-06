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
from anubis.handler import base
from anubis.util import pagination


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
        return self.now <= self.now < tdoc['begin_at']

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
            return 'Running...'
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
            problem.get_dict(self.domain_id, tdoc['pids'].values())
        )
        psdict = dict()
        rdict = dict()
        if tsdoc:
            attended = tsdoc.get('attend') == 1
            for pdetail in tsdoc.get('detail', []):
                psdict[pdetail['pid']] = pdetail
            rdict = await record.get_dict(psdoc['rid'] for psdoc in psdict.values())
        else:
            attended = False


