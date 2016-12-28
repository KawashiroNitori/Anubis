from pymongo import errors

from anubis import db
from anubis import error
from anubis.model import builtin
from anubis.util import argmethod
from anubis.util import validator

PROJECTION_PUBLIC = {'uid': 1}


@argmethod.wrap
async def add(domain_id: str, owner_uid: int,
              roles=builtin.DOMAIN_SYSTEM['roles'],
              name: str=None, gravatar: str=None):
    validator.check_domain_id(domain_id)
    validator.check_name(name)
    for domain in builtin.DOMAINS:
        if domain['_id'] == domain_id:
            raise error.DomainAlreadyExistError(domain_id)
    coll = db.Collection('domain')
    try:
        return await coll.insert({
            '_id': domain_id,
            'owner_uid': owner_uid,
            'roles': roles,
            'name': name,
            'gravatar': gravatar
        })
    except errors.DuplicateKeyError:
        raise error.DomainAlreadyExistError(domain_id) from None


@argmethod.wrap
async def get(domain_id: str, fields=None):
    for domain in builtin.DOMAINS:
        if domain['_id'] == domain_id:
            return domain
    coll = db.Collection('domain')
    return await coll.find_one(domain_id, fields)


def get_multi(*, fields=None, **kwargs):
    coll = db.Collection('domain')
    return coll.find(kwargs, fields)


@argmethod.wrap
async def edit(domain_id: str, **kwargs):

