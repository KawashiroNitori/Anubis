import datetime

from pymongo import errors

from anubis import db
from anubis import error
from anubis.model import builtin
from anubis.util import argmethod
from anubis.util import pwhash
from anubis.util import validator


PROJECTION_PUBLIC = {
    '_id': 1,
    'uname': 1,
    'uname_lower': 1,
    'gravatar': 1
}

PROJECTION_VIEW = {'salt': 0, 'hash': 0}
PROJECTION_ALL = None


@argmethod.wrap
async def add(uid: int, uname: str, password: str, mail: str, reg_ip: str='', priv: int=builtin.DEFAULT_PRIV):
    # Add a user.
    validator.check_uname(uname)
    # TODO: Filter name by keywords
    validator.check_password(password)
    validator.check_mail(mail)

    uname_lower = uname.strip().lower()
    mail_lower = mail.strip().lower()

    for user in builtin.USERS:
        if user['_id'] == uid or user['uname_lower'] == uname_lower or user['mail_lower'] == mail_lower:
            raise error.UserAlreadyExistError(uname)

    salt = pwhash.gen_salt()
    coll = db.Collection('user')
    try:
        await coll.insert_one({
            '_id': uid,
            'uname': uname,
            'uname_lower': uname_lower,
            'mail': mail,
            'mail_lower': mail_lower,
            'salt': salt,
            'hash': pwhash.hash_password(password, salt),
            'reg_at': datetime.datetime.utcnow(),
            'reg_ip': reg_ip,
            'priv': priv,
            'login_at': datetime.datetime.utcnow(),
            'login_ip': reg_ip,
            'gravatar': mail
        })
    except errors.DuplicateKeyError:
        raise error.UserAlreadyExistError(uid, uname, mail) from None


@argmethod.wrap
async def get_by_uid(uid: int, fields=PROJECTION_VIEW):
    for user in builtin.USERS:
        if user['_id'] == uid:
            return user
    coll = db.Collection('user')
    return await coll.find_one({'_id': uid}, fields)


@argmethod.wrap
async def get_by_mail(mail: str, fields=PROJECTION_VIEW):
    mail_lower = mail.strip().lower()
    for user in builtin.USERS:
        if user['mail_lower'] == mail_lower:
            return user
    coll = db.Collection('user')
    return await coll.find_one({'mail_lower': mail_lower}, fields)


@argmethod.wrap
async def get_by_uname(uname: str, fields=PROJECTION_VIEW):
    uname_lower = uname.strip().lower()
    for user in builtin.USERS:
        if user['uname_lower'] == uname_lower:
            return user
    coll = db.Collection('user')
    return await coll.find_one({'uname_lower': uname_lower}, fields)


def get_multi(*, fields=PROJECTION_VIEW, **kwargs):
    coll = db.Collection('user')
    return coll.find(kwargs, fields)


async def get_dict(uids, *, fields=PROJECTION_VIEW):
    result = dict()
    async for doc in get_multi(_id={'$in': list(set(uids))}, fields=fields):
        result[doc['_id']] = doc
        return result


@argmethod.wrap
async def check_password_by_uid(uid: int, password: str):
    doc = await get_by_uid(uid, PROJECTION_ALL)
    if doc and pwhash.check(password, doc['salt'], doc['hash']):
        return doc


@argmethod.wrap
async def check_password_by_uname(uname: str, password: str):
    doc = await get_by_uname(uname, PROJECTION_ALL)
    if doc and pwhash.check(password, doc['salt'], doc['hash']):
        return doc


@argmethod.wrap
async def set_password(uid: int, password: str):
    validator.check_password(password)
    salt = pwhash.gen_salt()
    coll = db.Collection('user')
    doc = await coll.find_one_and_update(filter={'_id': uid},
                                         update={'$set': {'salt': salt,
                                                          'hash': pwhash.hash_password(password, salt)}},
                                         return_document=True)
    return doc


@argmethod.wrap
async def set_mail(uid: int, mail: str):
    validator.check_mail(mail)
    return await set_by_uid(uid, mail=mail, mail_lower=mail.strip().lower())


@argmethod.wrap
async def change_password(uid: int, password: str):
    validator.check_password(password)
    salt = pwhash.gen_salt()
    coll = db.Collection('user')
    doc = await coll.find_one_and_update(filter={'_id': uid},
                                         update={'$set': {'salt': salt,
                                                          'hash': pwhash.hash_password(password, salt)}},
                                         return_document=True)
    return doc


@argmethod.wrap
async def set_mail(uid: int, mail: str):
    validator.check_mail(mail)
    return await set_by_uid(uid, mail=mail, mail_lower=mail.strip().lower())


@argmethod.wrap
async def change_password(uid: int, current_password: str, password: str):
    doc = await check_password_by_uid(uid, current_password)
    if not doc:
        return None
    validator.check_password(password)
    salt = pwhash.gen_salt()
    coll = db.Collection('user')
    doc = await coll.find_one_and_update(filter={'_id': doc['_id'],
                                                 'salt': doc['salt'],
                                                 'hash': doc['hash']},
                                         update={'$set': {'salt': salt,
                                                          'hash': pwhash.hash_password(password, salt)}},
                                         return_document=True)
    return doc


async def set_by_uid(uid, **kwargs):
    coll = db.Collection('user')
    doc = await coll.find_one_and_update(filter={'_id': uid}, update={'$set': kwargs}, return_document=True)
    return doc


@argmethod.wrap
async def get_prefix_list(prefix: str, fields=PROJECTION_VIEW, limit: int=50):
    prefix = prefix.lower()
    regex = '\\A\\Q{0}\\E'.format(prefix.replace('\\E', '\\E\\\\E\\Q'))
    coll = db.Collection('user')
    udocs = await (coll.find({'uname_lower': {'$regex': regex}}, fields=fields).to_list(limit))
    for udoc in builtin.USERS:
        if udoc['uname_lower'].startswith(prefix):
            udocs.append(udoc)
    return udocs


@argmethod.wrap
async def create_indexes():
    coll = db.Collection('user')
    await coll.create_index('uname_lower', unique=True)
    await coll.create_index('mail_lower', sparse=True)


if __name__ == '__main__':
    argmethod.invoke_by_args()
