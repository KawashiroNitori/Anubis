from anubis import app
from anubis.model import student
from anubis.model import builtin
from anubis.handler import base


@app.route('/student/search', 'student_search')
class StudentSearchHandler(base.Handler):
    @base.require_priv(builtin.PRIV_USER_PROFILE)
    @base.limit_rate('student_search', 60, 60)
    @base.get_argument
    @base.sanitize
    async def get(self, sid: str, id_num: str):
        sdoc = await student.check_student_by_id(sid, id_num)
        sdoc['id_number'] = sdoc['id_number'][-6:]
        self.json(sdoc)
