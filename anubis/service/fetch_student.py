import asyncio
from aiohttp import ClientSession
from urllib import parse
from bs4 import BeautifulSoup

from anubis import error
from anubis.util import argmethod
from anubis.util import options
from anubis.util import ocr


options.define('school_url', 'http://jwc.sut.edu.cn', 'URL of school server.')
options.define('school_login_method', 'ACTIONLOGON.APPPROCESS', 'Method of school login.')
options.define('school_captcha_method', 'ACTIONVALIDATERANDOMPICTURE.APPPROCESS', 'Method of captcha.')
options.define('school_student_method', 'ACTIONQUERYSTUDENTBYSTUDENTNO.APPPROCESS?mode=2',
               'Method of fetch student info.')
options.define('school_teacher_username', 'teacher', 'Username of school teacher account.')
options.define('school_teacher_pass', 'password', 'Password of school teacher account.')

_session = ClientSession(loop=asyncio.get_event_loop())


async def _get_captcha_image():
    global _session
    captcha_url = parse.urljoin(options.options.school_url, options.options.school_captcha_method)
    async with _session.get(captcha_url) as response:
        return await response.read()


async def _login():
    global _session
    login_url = parse.urljoin(options.options.school_url, options.options.school_login_method)

    for _ in range(5):
        bin_image = await _get_captcha_image()
        captcha = ocr.recognize_digits(bin_image)
        if not captcha:
            continue
        async with _session.post(login_url, data={'WebUserNO': options.options.school_teacher_username,
                                                  'Password': options.options.school_teacher_pass,
                                                  'Agnomen': captcha}) as response:
            text = await response.text(encoding='gbk')
            if '正确的附加码' in text:
                continue
            if '错误的用户名' in text or '操作权限' in text:
                raise error.InvalidTeacherError()
            break


@argmethod.wrap
async def fetch(student_id: str):
    global _session
    fetch_url = parse.urljoin(options.options.school_url, options.options.school_student_method)
    text = None
    for _ in range(3):
        async with _session.post(fetch_url, data={'ByStudentNO': student_id}) as response:
            text = await response.text(encoding='gbk')
            if '用户未登录' in text:
                text = ''
                await _login()
                continue
            break
    if not text:
        raise error.InvalidTeacherError()
    if '学校名称' not in text:
        return None
    page = BeautifulSoup(text, 'html.parser')
    tds = page.find_all('td')
    student = {'_id': tds[7].string,
               'university': tds[2].string,
               'college': tds[4].string,
               'attainment': tds[9].string,
               'name': tds[11].string,
               'major': tds[13].string,
               'gender': tds[15].string,
               'class': tds[17].string,
               'grade': int(tds[19].string),
               'id_number': tds[21].string,
               'ethnic': tds[23].string}
    return student


if __name__ == '__main__':
    argmethod.invoke_by_args()
