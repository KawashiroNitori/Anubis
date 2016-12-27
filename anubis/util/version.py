import functools
import git
import logging
from os import path

import anubis
from anubis.util import argmethod

_logger = logging.getLogger(__name__)


@functools.lru_cache()
@argmethod.wrap
def get():
    try:
        return git.Repo(path.dirname(path.dirname(anubis.__file__))).git.describe(always=True, dirty=True)
    except (git.InvalidGitRepositoryError, git.GitCommandError) as e:
        _logger.error('Failed to get respository: %s', repr(e))
        return 'unknown'


if __name__ == '__main__':
    argmethod.invoke_by_args()