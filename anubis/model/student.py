import logging

from anubis import db
from anubis import error
from anubis.service import fetch_student
from anubis.util import argmethod


_logger = logging.getLogger(__name__)


@argmethod.wrap
async def add(sid: str, **kwargs):
    coll = db.Collection('student')
    return (await coll.insert_one({'_id': sid, **kwargs})).inserted_id


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
        await add(sid=sdoc['_id'], **sdoc)
    return sdoc


def get_multi(*, projection=None, **kwargs):
    coll = db.Collection('student')
    return coll.find(kwargs, projection)


async def get_list(sids: list):
    result = []
    async for student in get_multi(_id={'$in': list(set(sids))}):
        result.append(student)
    return result


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

async def main():
    for s_id in range(170405101, 170405350):
        if s_id % 100 >= 50:
            continue
        student = await get(str(s_id))
    for s_id in range(171203101, 171203850):
        if s_id % 100 >= 50:
            continue
        student = await get(str(s_id))
    for s_id in range(171201101, 171201650):
        if s_id % 100 >= 50:
            continue
        student = await get(str(s_id))
        
if __name__ == '__main__':
    argmethod.invoke_by_args()
