import logging

from anubis import db
from anubis import error
from anubis.service import fetch_student
from anubis.util import argmethod


_logger = logging.getLogger(__name__)


@argmethod.wrap
async def add(*, _id: str, **kwargs):
    coll = db.Collection('student')
    return (await coll.insert_one({'_id': _id, **kwargs})).inserted_id


@argmethod.wrap
async def get(student_id: str):
    coll = db.Collection('student')
    sdoc = await coll.find_one(student_id)
    if not sdoc:
        try:
            sdoc = await fetch_student.fetch(student_id)
        except Exception as e:
            _logger.exception('Exception occurred when fetching student information: {0}'.format(repr(e)))
            return None
        if not sdoc:
            return None
        await add(**sdoc)
    return sdoc


@argmethod.wrap
async def check_student_by_id(student_id: str, id_number_last_6digit: str):
    sdoc = await get(student_id)
    if not sdoc or sdoc['id_number'][-6:].upper() != id_number_last_6digit.upper():
        raise error.StudentNotFoundError(student_id)
    return sdoc


@argmethod.wrap
async def create_indexes():
    coll = db.Collection('student')
    await coll.create_index('name')
    await coll.create_index('grade')
    await coll.create_index('id_number', unique=True)
    await coll.create_index('class')


if __name__ == '__main__':
    argmethod.invoke_by_args()
