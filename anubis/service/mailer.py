from aiohttp import ClientSession

from anubis.util import argmethod
from anubis.util import options

options.define('mail_from', default='acm@sutacm.cn', help='Mail from')
options.define('mail_api_user', default='api_user', help='SendCloud API User')
options.define('mail_api_key', default='api_key', help='SendCloud API Key')


@argmethod.wrap
async def send_mail(to: str, subject: str, content: str):
    data = {
        'apiUser': options.options.mail_api_user,
        'apiKey': options.options.mail_api_key,
        'to': to,
        'from': options.options.mail_from,
        'fromName': 'ACM 实验室',
        'subject': subject,
        'html': content,
    }

    async with ClientSession() as session:
        async with session.post('http://api.sendcloud.net/apiv2/mail/send', data=data) as response:
            return await response.json()


if __name__ == '__main__':
    argmethod.invoke_by_args()
