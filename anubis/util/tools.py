import logging
import pkgutil
from os import path

from anubis.util import argmethod

_logger = logging.getLogger(__name__)


@argmethod.wrap
async def create_all_indexes():
    model_path = path.join(path.dirname(path.dirname(__file__)), 'model')
    for model_finder, name, isPkg in pkgutil.iter_modules([model_path]):
        if not isPkg:
            module = model_finder.find_module(name).load_module()
            if 'create_indexes' in dir(module):
                _logger.info('Creating indexes for "%s".' % name)
                await module.create_indexes()


if __name__ == '__main__':
    argmethod.invoke_by_args()
