import datetime

from pymongo import errors
from pymongo import ReturnDocument

from anubis import error
from anubis import db
from anubis.util import argmethod
from anubis.util import validator
from anubis.util import pwhash
from anubis.util.orderedset import OrderedSet
from anubis.model import domain
from anubis.model import contest
from anubis.model import user
from anubis.model import builtin


@argmethod.wrap
async def add(campaign_id: str, title: str, content: str, owner_uid: int,
              begin_at: lambda i: datetime.datetime.utcfromtimestamp(int(i)),
              end_at: lambda i: datetime.datetime.utcfromtimestamp(int(i)),
              is_newbie: bool):
    validator.check_title(title)
    validator.check_content(content)
    validator.check_domain_id(campaign_id)
    if begin_at >= end_at:
        raise error.ValidationError('begin_at', 'end_at')
    coll = db.Collection('campaign')
    try:
        return (await coll.insert_one({'_id': campaign_id,
                                       'domain_id': builtin.DOMAIN_ID_SYSTEM,
                                       'owner_uid': owner_uid,
                                       'title': title,
                                       'content': content,
                                       'is_newbie': is_newbie,
                                       'begin_at': begin_at,
                                       'end_at': end_at})).inserted_id
    except errors.DuplicateKeyError:
        raise error.CampaignAlreadyExistError(campaign_id) from None


@argmethod.wrap
async def get(campaign_id: str, projection=None):
    coll = db.Collection('campaign')
    cdoc = await coll.find_one(campaign_id, projection)
    if not cdoc:
        raise error.ContestNotFoundError(campaign_id)
    return cdoc


def get_multi(*, projection=None, **kwargs):
    coll = db.Collection('campaign')
    return coll.find(kwargs, projection)


@argmethod.wrap
async def get_list(projection=None, limit: int=None, **kwargs):
    coll = db.Collection('campaign')
    return await coll.find(kwargs, projection).limit(limit).to_list(None)


@argmethod.wrap
async def edit(campaign_id: str, **kwargs):
    coll = db.Collection('campaign')
    cdoc = await coll.find_one(campaign_id)
    if 'owner_uid' in kwargs:
        del kwargs['owner_uid']
    if 'title' in kwargs:
        validator.check_title(kwargs['title'])
    if 'content' in kwargs:
        validator.check_content(kwargs['content'])
    begin_at = kwargs['begin_at'] if 'begin_at' in kwargs else cdoc['begin_at']
    end_at = kwargs['end_at'] if 'end_at' in kwargs else cdoc['end_at']
    if begin_at >= end_at:
        raise error.ValidationError('begin_at', 'end_at')
    return await coll.find_one_and_update(filter={'_id': campaign_id},
                                          update={'$set': {**kwargs}},
                                          return_document=ReturnDocument.AFTER)


@argmethod.wrap
async def get_team(campaign_id: str, team_name: str):
    coll = db.Collection('campaign.team')
    team = await coll.find_one({'cid': campaign_id, 'team_name': team_name})
    if not team:
        raise error.CampaignTeamNotFoundError(campaign_id, team_name)
    return team


def get_multi_team(*, projection=None, **kwargs):
    coll = db.Collection('campaign.team')
    return coll.find(kwargs, projection)


@argmethod.wrap
async def get_team_by_uid(campaign_id: str, uid: int):
    coll = db.Collection('campaign.team')
    team = await coll.find_one({'cid': campaign_id, 'uid': uid})
    return team


@argmethod.wrap
async def get_team_by_member(campaign_id: str, student_id: str):
    coll = db.Collection('campaign.team')
    return await coll.find_one({'cid': campaign_id, 'members': student_id})


@argmethod.wrap
async def get_list_team(campaign_id: str):
    coll = db.Collection('campaign.team')
    return await coll.find({'cid': campaign_id}).to_list(None)


@argmethod.wrap
async def get_team_count(campaign_id: str):
    return await get_multi_team(cid=campaign_id).count()


@argmethod.wrap
async def attend(campaign_id: str, uid: int, mail: str, tel: str, team_name: str, is_newbie: bool, members: list):
    validator.check_mail(mail)
    validator.check_tel(tel)
    validator.check_team_name(team_name)
    members = list(OrderedSet(members))
    coll = db.Collection('campaign.team')
    try:
        return await coll.find_one_and_update(filter={'cid': campaign_id,
                                                      'uid': uid},
                                              update={'$set': {'mail': mail,
                                                               'tel': tel,
                                                               'team_name': team_name,
                                                               'is_newbie': is_newbie,
                                                               'members': members}},
                                              upsert=True,
                                              return_document=ReturnDocument.AFTER)
    except errors.DuplicateKeyError:
        raise error.CampaignTeamAlreadyExistError(members, team_name)


async def update_user_for_teams(teams_list_or_tuple):
    for index, team in enumerate(teams_list_or_tuple, 1):
        if isinstance(team, tuple):
            team_uname = team[0]
            team_doc = team[1]
        else:
            team_uname = 'team{0}'.format(index)
            team_doc = team
        udoc = await user.get_by_uname(team_uname)
        plain_pass = pwhash.gen_password()
        extra_info = {'plain_pass': plain_pass,
                      'nickname': team_doc['team_name']}
        if not udoc:
            await user.add(team_uname, plain_pass, team_doc['mail'], **extra_info)
        else:
            await user.update(udoc['_id'], **extra_info)
            await user.set_password(udoc['_id'], plain_pass)


async def attend_contest_for_teams(team_unames, domain_id: str, tid: int):
    await contest.get(domain_id, tid)
    for team_uname in team_unames:
        udoc = await user.get_by_uname(team_uname)
        if not udoc:
            raise error.UserNotFoundError(team_uname)
        await domain.set_user_role(domain_id, udoc['_id'], builtin.ROLE_DEFAULT)
        await contest.attend(domain_id, tid, udoc['_id'])


@argmethod.wrap
async def create_indexes():
    coll = db.Collection('campaign')
    await coll.create_index('owner_uid')
    await coll.create_index([('begin_at', 1),
                             ('end_at', 1)])
    team_coll = db.Collection('campaign.team')
    await team_coll.create_index([('cid', 1),
                                  ('uid', 1)], unique=True)
    await team_coll.create_index([('cid', 1),
                                  ('members', 1)], sparse=True)
    await team_coll.create_index([('cid', 1),
                                  ('team_name', 1)])


if __name__ == '__main__':
    argmethod.invoke_by_args()
