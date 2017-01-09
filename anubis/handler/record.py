import asyncio
import datetime
import io
import zipfile
from bson import objectid

from anubis import app
from anubis import constant
from anubis import error
from anubis.handler import base
from anubis.model import builtin
from anubis.model import domain
from anubis.model import record
from anubis.model import user
from anubis.model import problem
from anubis.model import testdata
from anubis.service import bus


@app.route('/records', 'record_main')
class RecordMainHandler(base.Handler):
    async def get(self):
        # TODO: projection, pagination
        rdocs = await record.get_all_multi(
            get_hidden=self.has_priv(builtin.PRIV_VIEW_HIDDEN_RECORD)
        ).sort([('_id', -1)]).to_list(50)
        # TODO: projection
        udict, pdict = await asyncio.gather(
            user.get_dict(rdoc['uid'] for rdoc in rdocs),
            problem.get_dict((rdoc['domain_id'], rdoc['pid']) for rdoc in rdocs)
        )
        self.render('record_main.html', rdocs=rdocs, udict=udict, pdict=pdict)


@app.connection_route('/records-conn', 'record_main-conn')
class RecordMainConnection(base.Connection):
    async def on_open(self):
        await super(RecordMainConnection, self).on_open()
        bus.subscribe(self.on_record_change, ['record_change'])

    async def on_record_change(self, e):
        rdoc = await record.get(objectid.ObjectId(e['value']), record.PROJECTION_PUBLIC)
        # TODO: check permission for visibility: contest
        udoc, pdoc = await asyncio.gather(user.get_by_uid(rdoc['uid']),
                                          problem.get(rdoc['domain_id'], rdoc['pid']))
        if pdoc.get('hidden', False) and not self.has_perm(builtin.PERM_VIEW_PROBLEM_HIDDEN):
            pdoc = None
        # TODO: remove the rdoc sent.
        self.send(html=self.render_html('record_main_tr.html', rdoc=rdoc, udoc=udoc, pdoc=pdoc),
                  rdoc=rdoc)

    async def on_close(self):
        bus.unsubscribe(self.on_record_change)


@app.route('/records/{rid}', 'record_detail')
class RecordDetailHandler(base.Handler):
    @base.route_argument
    @base.sanitize
    async def get(self, *, rid: objectid.ObjectId):
        rdoc = await record.get(rid)
        if not rdoc:
            raise error.RecordNotFoundError(rid)
        # TODO: Check domain permission, permission for visibility in place.
        if rdoc['domain_id'] != self.domain_id:
            self.redirect(self.reverse_url('record_detail', rid=rid, domain_id=rdoc['domain_id']))
            return
        # TODO: Check permission for visibility: contest
        show_status = True  # Temporary
        if (not self.own(rdoc, field='uid')
            and not self.has_perm(builtin.PERM_READ_RECORD_CODE)
            and not self.has_priv(builtin.PRIV_READ_RECORD_CODE)):
            del rdoc['code']
        if not show_status and 'code' not in rdoc:
            raise error.PermissionError(builtin.PERM_VIEW_CONTEST_HIDDEN_STATUS)
        udoc, dudoc, pdoc = await asyncio.gather(user.get_by_uid(rdoc['uid']),
                                                 domain.get_user(self.domain_id, rdoc['uid']),
                                                 problem.get(rdoc['domain_id'], rdoc['pid']))
        if pdoc.get('hidden', False) and not self.has_perm(builtin.PERM_VIEW_PROBLEM_HIDDEN):
            pdoc = None
        self.render('record_detail.html', rdoc=rdoc, udoc=udoc, dudoc=dudoc, pdoc=pdoc,
                    show_status=show_status)


@app.route('/records/{rid}/rejudge', 'record_rejudge')
class RecordRejudgeHandler(base.Handler):
    @base.route_argument
    @base.post_argument
    @base.require_csrf_token
    @base.sanitize
    async def post(self, *, rid: objectid.ObjectId):
        rdoc = await record.get(rid)
        if rdoc['domain_id'] == self.domain_id:
            self.check_perm(builtin.PERM_REJUDGE)
        else:
            self.check_priv(builtin.PRIV_REJUDGE)
        await record.rejudge(rdoc['_id'])
        self.json_or_redirect(self.referer_or_main)


@app.route('/records/{rid}/data', 'record_pretest_data')
class RecordPretestDataHandler(base.Handler):
    @base.route_argument
    @base.sanitize
    async def get(self, *, rid: objectid.ObjectId):
        rdoc = await record.get(rid)
        if not rdoc or rdoc['type'] != constant.record.TYPE_PRETEST:
            raise error.RecordNotFoundError(rid)
        if not self.own(rdoc, builtin.PRIV_READ_PRETEST_DATA, 'uid'):
            self.check_priv(builtin.PRIV_READ_PRETEST_DATA)
        ddoc = await testdata.get(rdoc['domain_id'], rdoc['data_id'])
        if not ddoc:
            raise error.RecordDataNotFoundError(rdoc['_id'])

        output_buffer = io.BytesIO()
        zip_file = zipfile.ZipFile(output_buffer, 'a', zipfile.ZIP_DEFLATED)
        config_content = str(len(ddoc['content'])) + '\n'
        for i, (data_input, data_output) in enumerate(ddoc['content']):
            input_file = 'input{0}.txt'.format(i)
            output_file = 'output{0}.txt'.format(i)
            config_content +='{0}|{1}|1|10|262144\n'.format(input_file, output_file)
            zip_file.writestr('Input/{0}'.format(input_file), data_input)
            zip_file.writestr('Output/{0}'.format(output_file), data_output)
        zip_file.writestr('Config.ini', config_content)
        for zfile in zip_file.filelist:
            zfile.create_system = 0
        zip_file.close()

        await self.binary(output_buffer.getvalue(), 'application/zip')
