import collections

from anubis import app
from anubis.model import builtin
from anubis.model import domain
from anubis.model import user
from anubis.handler import base


@app.route('/', 'domain_main')
class DomainMainHandler(base.Handler):
    async def get(self):
        self.render('domain_main.html')
