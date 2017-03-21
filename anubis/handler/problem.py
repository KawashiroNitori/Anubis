import asyncio
import functools
import hashlib
import datetime
from bson import objectid

from anubis import app
from anubis import error
from anubis import constant
from anubis.handler import base
from anubis.model import builtin
from anubis.model import user
from anubis.model import problem
from anubis.model import domain
from anubis.model import fs
from anubis.model import testdata
from anubis.model import record
from anubis.model import contest
from anubis.util import pagination
from anubis.util import json
from anubis.util import validator
from anubis.service import bus


async def render_or_json_problem_list(self, page, ppcount, pcount, pdocs, category, psdict, **kwargs):
    if 'page_title' not in kwargs:
        kwargs['page_title'] = self.translate(self.TITLE)
    if 'path_components' not in kwargs:
        kwargs['path_components'] = self.build_path((self.translate(self.NAME), None))
    if self.prefer_json:
        list_html = self.render_html('partials/problem_list.html', page=page, ppcount=ppcount,
                                     pcount=pcount, pdocs=pdocs, psdict=psdict)
        stat_html = self.render_html('partials/problem_stat.html', pcount=pcount)
        path_html = self.render_html('partials/path.html', path_components=kwargs['path_components'])
        self.json({'title': self.render_title(kwargs['page_title']),
                   'fragments': [{'html': list_html},
                                 {'html': stat_html},
                                 {'html': path_html}]})
    else:
        self.render('problem_main.html', page=page, ppcount=ppcount, pcount=pcount, pdocs=pdocs,
                    category=category, psdict=psdict, **kwargs)


@app.route('/p', 'problem_main')
class ProblemMainHandler(base.OperationHandler):
    PROBLEMS_PER_PAGE = 100

    @base.require_perm(builtin.PERM_VIEW_PROBLEM)
    @base.get_argument
    @base.sanitize
    async def get(self, *, page: int = 1):
        # TODO: projection
        if not self.has_perm(builtin.PERM_VIEW_PROBLEM_HIDDEN):
            f = {'hidden': False}
        else:
            f = {}
        pdocs, ppcount, pcount = await pagination.paginate(
            problem.get_multi(domain_id=self.domain_id, **f).sort([('_id', 1)]),
            page, self.PROBLEMS_PER_PAGE)
        if self.has_priv(builtin.PRIV_USER_PROFILE):
            # TODO: projection
            psdict = await problem.get_dict_status(self.domain_id,
                                                   self.user['_id'],
                                                   (pdoc['_id'] for pdoc in pdocs))
        else:
            psdict = None
        await render_or_json_problem_list(self, page=page, ppcount=ppcount, pcount=pcount,
                                          pdocs=pdocs, category='', psdict=psdict)

    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_csrf_token
    @base.sanitize
    async def star_unstar(self, *, pid: int, star: bool):
        pdoc = await problem.get(self.domain_id, pid)
        pdoc = await problem.set_star(self.domain_id, pdoc['_id'], self.user['_id'], star)
        self.json_or_redirect(self.url, star=pdoc['star'])

    post_star = functools.partialmethod(star_unstar, star=True)
    post_unstar = functools.partialmethod(star_unstar, star=False)


@app.route('/p/category/{category:.*}', 'problem_category')
class ProblemCategoryHandler(base.OperationHandler):
    PROBLEMS_PER_PAGE = 100

    @staticmethod
    def my_split(string, delim):
        return list(filter(lambda s: bool(s), map(lambda s: s.strip(), string.split(delim))))

    @staticmethod
    def build_query(query_string):
        category_groups = ProblemCategoryHandler.my_split(query_string, ' ')
        if not category_groups:
            return {}
        query = {'$or': []}
        for g in category_groups:
            categories = ProblemCategoryHandler.my_split(g, ',')
            if not categories:
                continue
            sub_query = {'$and': []}
            for c in categories:
                sub_query['$and'].append({'tag': c})
            query['$or'].append(sub_query)
        return query

    @base.require_perm(builtin.PERM_VIEW_PROBLEM)
    @base.get_argument
    @base.route_argument
    @base.sanitize
    async def get(self, *, category: str, page: int=1):
        if not self.has_perm(builtin.PERM_VIEW_PROBLEM_HIDDEN):
            f = {'hidden': False}
        else:
            f = {}
        query = ProblemCategoryHandler.build_query(category)
        pdocs, ppcount, pcount = await pagination.paginate(problem.get_multi(domain_id=self.domain_id,
                                                                             **query,
                                                                             **f).sort([('_id', 1)]),
                                                           page, self.PROBLEMS_PER_PAGE)
        if self.has_priv(builtin.PRIV_USER_PROFILE):
            psdict = await problem.get_dict_status(self.domain_id,
                                                   self.user['_id'],
                                                   (pdoc['_id'] for pdoc in pdocs))
        else:
            psdict = None
        page_title = category or self.translate('(All Problems)')
        path_components = self.build_path(
            (self.translate('problem_main'), self.reverse_url('problem_main')),
            (page_title, None)
        )
        await render_or_json_problem_list(self, page=page, ppcount=ppcount, pcount=pcount,
                                          pdocs=pdocs, category=category, psdict=psdict,
                                          page_title=page_title, path_components=path_components)


@app.route('/p/{pid:-?\d+|\w{24}}', 'problem_detail')
class ProblemDetailHandler(base.Handler):
    @base.require_perm(builtin.PERM_VIEW_PROBLEM)
    @base.route_argument
    @base.sanitize
    async def get(self, *, pid: int):
        uid = self.user['_id'] if self.has_priv(builtin.PRIV_USER_PROFILE) else None
        pdoc = await problem.get(self.domain_id, pid, uid)
        if pdoc.get('hidden', False):
            self.check_perm(builtin.PERM_VIEW_PROBLEM_HIDDEN)
        udoc = await user.get_by_uid(pdoc['owner_uid'])
        # TODO: tdoc
        path_components = self.build_path(
            (self.translate('problem_main'), self.reverse_url('problem_main')),
            (pdoc['title'], None)
        )
        self.render('problem_detail.html', pdoc=pdoc, udoc=udoc,
                    page_title=pdoc['title'], path_components=path_components)


@app.route('/p/{pid}/submit', 'problem_submit')
class ProblemSubmitHandler(base.Handler):
    @base.require_perm(builtin.PERM_SUBMIT_PROBLEM)
    @base.route_argument
    @base.sanitize
    async def get(self, *, pid: int):
        # TODO: check status, eg. test, hidden problem, ...
        uid = self.user['_id'] if self.has_priv(builtin.PRIV_USER_PROFILE) else None
        pdoc = await problem.get(self.domain_id, pid, uid)
        if pdoc.get('hidden', False):
            self.check_perm(builtin.PERM_VIEW_PROBLEM_HIDDEN)
        udoc = await user.get_by_uid(pdoc['owner_uid'])
        if uid is None:
            rdocs = []
        else:
            # TODO: needs to be in sync with contest_detail_problem_submit
            rdocs = await record.get_user_in_problem_multi(
                uid, self.domain_id, pdoc['_id']
            ).sort([('_id', -1)]).to_list(10)
        for rdoc in rdocs:
            rdoc['url'] = self.reverse_url('record_detail', rid=rdoc['_id'])
        path_components = self.build_path(
            (self.translate('problem_main'), self.reverse_url('problem_main')),
            (pdoc['title'], self.reverse_url('problem_detail', pid=pdoc['_id'])),
            (self.translate('problem_submit'), None)
        )
        self.json_or_render('problem_submit.html', pdoc=pdoc, udoc=udoc, rdocs=rdocs,
                            page_title=pdoc['title'], path_components=path_components)

    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_perm(builtin.PERM_SUBMIT_PROBLEM)
    @base.route_argument
    @base.post_argument
    @base.require_csrf_token
    @base.sanitize
    async def post(self, *, pid: int, lang: str, code: str):
        # TODO: check status, eg. test, hidden problem, ...
        pdoc = await problem.get(self.domain_id, pid)
        if pdoc.get('hidden', False):
            self.check_perm(builtin.PERM_VIEW_PROBLEM_HIDDEN)
        pdoc = await problem.inc(self.domain_id, pid, 'num_submit', 1)
        rid = await record.add(self.domain_id, pdoc['_id'], constant.record.TYPE_SUBMISSION,
                               self.user['_id'], lang, code)
        self.json_or_redirect(self.reverse_url('record_detail', rid=rid))


@app.route('/p/{pid}/pretest', 'problem_pretest')
class ProblemPretestHandler(base.Handler):
    @base.require_perm(builtin.PERM_SUBMIT_PROBLEM)
    @base.route_argument
    @base.post_argument
    @base.require_csrf_token
    @base.sanitize
    async def post(self, *, pid: int, lang: str, code: str, data_input: str, data_output: str):
        # TODO: check status, eg. test, hidden problem, ...
        pdoc = await problem.get(self.domain_id, pid)
        if pdoc['judge_mode'] == constant.record.MODE_SUBMIT_ANSWER:
            raise error.ProblemCannotPretestError(pid)
        # Don't need to check hidden status
        data = list(zip(self.request.POST.getall('data_input'),
                        self.request.POST.getall('data_output')))
        did = await testdata.add(self.domain_id, data, self.user['_id'], testdata.TYPE_PRETEST_DATA,
                                 pid=pdoc['_id'])
        rid = await record.add(self.domain_id, pdoc['_id'], constant.record.TYPE_PRETEST,
                               self.user['_id'], lang, code, did)
        self.json_or_redirect(self.reverse_url('record_detail', rid=rid))


@app.connection_route('/p/{pid:\d{4,}}/pretest-conn', 'problem_pretest-conn')
class ProblemPretestConnection(base.Connection):
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    async def on_open(self):
        await super(ProblemPretestConnection, self).on_open()
        try:
            num_pid = int(self.request.match_info['pid'])
        except ValueError:
            num_pid = self.request.match_info['pid']
        self.pid = num_pid
        bus.subscribe(self.on_record_change, ['record_change'])

    async def on_record_change(self, e):
        rdoc = await record.get(objectid.ObjectId(e['value']), record.PROJECTION_PUBLIC)
        if rdoc['uid'] != self.user['_id'] or rdoc['domain_id'] != self.domain_id or rdoc['pid'] != self.pid:
            return
        # check permission fro visibility: contest
        if rdoc['tid']:
            now = datetime.datetime.utcnow()
            tdoc = await contest.get(rdoc['domain_id'], rdoc['tid'])
            if (not contest.RULES[tdoc['rule']].show_func(tdoc, now)
                and (self.domain_id != tdoc['domain_id']
                     or not self.has_perm(builtin.PERM_VIEW_CONTEST_HIDDEN_STATUS))
                    or (rdoc['status'] == constant.record.STATUS_JUDGING and len(rdoc['cases'])
                        and not (self.has_perm(builtin.PERM_READ_RECORD_DETAIL)
                                 or self.has_priv(builtin.PRIV_READ_RECORD_DETAIL)))):
                return
        # TODO: join form event to improve performance?
        rdoc['url'] = self.reverse_url('record_detail', rid=rdoc['_id'])
        self.send(rdoc=rdoc)

    async def on_close(self):
        bus.unsubscribe(self.on_record_change)


@app.route('/p/{pid}/data', 'problem_data')
class ProblemDataHandler(base.Handler):
    @base.route_argument
    @base.sanitize
    async def stream_data(self, *, pid: int, headers_only: bool=False):
        pdoc = await problem.get(self.domain_id, pid)
        if (not self.own(pdoc, builtin.PERM_READ_PROBLEM_DATA_SELF)
            and not self.has_perm(builtin.PERM_READ_PROBLEM_DATA)):
            self.check_priv(builtin.PERM_READ_PROBLEM_DATA)
        grid_out = await problem.get_data(self.domain_id, pid)

        self.response.content_type = grid_out.content_type or 'application/zip'
        self.response.last_modified = grid_out.update_date
        self.response.headers['Etag'] = '"{0}"'.format(grid_out.md5)
        # TODO: Handle If-Modified-Since & If-None-Match here.
        self.response.content_length = grid_out.length

        if not headers_only:
            await self.response.prepare(self.request)
            # TODO: Range
            remaining = grid_out.length
            chunk = await grid_out.readchunk()
            while chunk and remaining >= len(chunk):
                self.response.write(chunk)
                remaining -= len(chunk)
                _, chunk = await asyncio.gather(self.response.drain(), grid_out.readchunk())
            if chunk:
                self.response.write(chunk[:remaining])
                await self.response.drain()
            await self.response.write_eof()
    head = functools.partialmethod(stream_data, headers_only=True)
    get = stream_data


@app.route('/p/create', 'problem_create')
class ProblemCreateHandler(base.Handler):
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_perm(builtin.PERM_CREATE_PROBLEM)
    async def get(self):
        self.render('problem_edit.html')

    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_perm(builtin.PERM_CREATE_PROBLEM)
    @base.post_argument
    @base.require_csrf_token
    @base.sanitize
    async def post(self, *, title: str, content: str, hidden: bool=False,
                   time_second: int=1, memory_mb: int=64,
                   judge_mode: int=constant.record.MODE_COMPARE_IGNORE_BLANK,
                   data: objectid.ObjectId=None):
        validator.check_time_second_limit(time_second)
        validator.check_memory_mb_limit(memory_mb)
        time_ms = time_second * 1000
        memory_kb = memory_mb * 1024
        pid = await problem.add(self.domain_id, title, content, self.user['_id'],
                                hidden=hidden, time_ms=time_ms, memory_kb=memory_kb,
                                judge_mode=judge_mode, data=data)
        self.json_or_redirect(self.reverse_url('problem_detail', pid=pid))


@app.route('/p/{pid}/edit', 'problem_edit')
class ProblemEditHandler(base.Handler):
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_perm(builtin.PERM_EDIT_PROBLEM)
    @base.route_argument
    @base.sanitize
    async def get(self, *, pid: int):
        uid = self.user['_id'] if self.has_priv(builtin.PRIV_USER_PROFILE) else None
        pdoc = await problem.get(self.domain_id, pid, uid)
        udoc = await user.get_by_uid(pdoc['owner_uid'])
        path_coponents = self.build_path(
            (self.translate('problem_main'), self.reverse_url('problem_main')),
            (pdoc['title'], self.reverse_url('problem_detail', pid=pdoc['_id'])),
            (self.translate('problem_edit'), None)
        )
        self.render('problem_edit.html', pdoc=pdoc, udoc=udoc,
                    page_title=pdoc['title'], path_coponents=path_coponents)

    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_perm(builtin.PERM_EDIT_PROBLEM)
    @base.route_argument
    @base.post_argument
    @base.require_csrf_token
    @base.sanitize
    async def post(self, *, pid: int, title: str, content: str, hidden: bool=False,
                   time_second: int=1, memory_mb: int=64,
                   judge_mode: int=constant.record.MODE_COMPARE_IGNORE_BLANK,
                   data: objectid.ObjectId=None):
        validator.check_time_second_limit(time_second)
        validator.check_memory_mb_limit(memory_mb)
        time_ms = time_second * 1000
        memory_kb = memory_mb * 1024
        await problem.edit(self.domain_id, pid, title=title, content=content, hidden=hidden,
                           time_ms=time_ms, memory_kb=memory_kb, judge_mode=judge_mode)
        self.json_or_redirect(self.reverse_url('problem_detail', pid=pid))


@app.route('/p/{pid}/settings', 'problem_settings')
class ProblemSettingsHandler(base.Handler):
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_perm(builtin.PERM_EDIT_PROBLEM)
    @base.route_argument
    @base.sanitize
    async def get(self, *, pid: int):
        uid = self.user['_id'] if self.has_priv(builtin.PRIV_USER_PROFILE) else None
        pdoc = await problem.get(self.domain_id, pid, uid)
        udoc = await user.get_by_uid(pdoc['owner_uid'])
        path_components = self.build_path(
            (self.translate('problem_main'), self.reverse_url('problem_main')),
            (pdoc['title'], self.reverse_url('problem_detail', pid=pdoc['_id'])),
            (self.translate('problem_settings'), None)
        )
        self.render('problem_settings.html', pdoc=pdoc, udoc=udoc, page_title=pdoc['title'],
                    path_components=path_components)


@app.route('/p/{pid}/upload', 'problem_upload')
class ProblemSettingsHandler(base.Handler):
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_perm(builtin.PERM_EDIT_PROBLEM)
    @base.route_argument
    @base.sanitize
    async def get(self, *, pid: int):
        pdoc = await problem.get(self.domain_id, pid)
        if (not self.own(pdoc, builtin.PERM_READ_PROBLEM_DATA_SELF)
            and not self.has_perm(builtin.PERM_READ_PROBLEM_DATA)):
            self.check_priv(builtin.PRIV_READ_PROBLEM_DATA)
        self.render('problem_upload.html', pdoc=pdoc)

    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.require_perm(builtin.PERM_EDIT_PROBLEM)
    @base.route_argument
    @base.post_argument
    @base.require_csrf_token
    @base.sanitize
    async def post(self, *, pid: int, file: lambda _: _):
        pdoc = await problem.get(self.domain_id, pid)
        if (not self.own(pdoc, builtin.PERM_READ_PROBLEM_DATA_SELF)
            and not self.has_perm(builtin.PERM_READ_PROBLEM_DATA)):
            self.check_priv(builtin.PRIV_READ_PROBLEM_DATA)
        if file:
            data = file.file.read()
            try:
                data_dict = json.decode(data.decode('utf-8'))
            except Exception:
                self.json_or_redirect(self.url)
                return
            if pdoc['data']:
                await testdata.delete(self.domain_id, pdoc['data'])
            did = await testdata.add(self.domain_id, data_dict, self.user['_id'], testdata.TYPE_TEST_DATA,
                                     pid=pdoc['_id'])
            """
            md5 = hashlib.md5(data).hexdigest()
            fid = await fs.link_by_md5(md5)
            if not fid:
                fid = await fs.add_data(data)
            if pdoc.get('data'):
                await fs.unlink(pdoc['data'])
            """
            await problem.set_data(self.domain_id, pid, did)
        self.json_or_redirect(self.url)


@app.route('/p/{pid}/statistics', 'problem_statistics')
class ProblemStatisticsHandler(base.Handler):
    @base.route_argument
    @base.sanitize
    async def get(self, *, pid: int):
        uid = self.user['_id'] if self.has_priv(builtin.PRIV_USER_PROFILE) else None
        pdoc = await problem.get(self.domain_id, pid, uid)
        if pdoc.get('hidden', False):
            self.check_perm(builtin.PERM_VIEW_PROBLEM_HIDDEN)
        udoc = await user.get_by_uid(pdoc['owner_uid'])
        path_components = self.build_path(
            (self.translate('problem_main'), self.reverse_url('problem_main')),
            (pdoc['title'], self.reverse_url('problem_detail', pid=pdoc['_id'])),
            (self.translate('problem_statistics'), None)
        )
        self.render('problem_statistics.html', pdoc=pdoc, udoc=udoc, page_title=pdoc['title'],
                    path_components=path_components)
