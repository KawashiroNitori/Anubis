import asyncio
import collections
import datetime
import itertools

from bson import objectid
from pymongo import errors
from pymongo import ReturnDocument

from anubis import error
from anubis import db
from anubis.service import smallcache
from anubis.util import argmethod
from anubis.util import validator

ALLOWED_DOC_TYPES = ['problem', 'contest']


def node_id(ddoc):
    if ddoc['parent_type'] == 'discussion_node':
        return ddoc['parent_id']
    else:
        return ddoc['parent_type'], ddoc['parent_id']


@argmethod.wrap
async def get_node(domain_id: str, node_name: str):
    coll = db.Collection('discussion.node')
    return await coll.find_one({'domain_id': domain_id,
                                'name': node_name})


@argmethod.wrap
async def get_nodes(domain_id: str):
    coll = db.Collection('discussion.node')
    category_list = await coll.aggregate([
        {'$match': {'domain_id': domain_id}},
        {'$group': {'_id': '$category_name', 'nodes': {'$push': '$name'}}}
    ]).to_list(None)
    return collections.OrderedDict([
        (category['_id'], category['nodes']) for category in category_list])


@argmethod.wrap
async def add_node(domain_id: str, category_name: str, node_name: str, node_pic: str=None):
    validator.check_node_name(node_name)
    if await get_node(domain_id, node_name):
        raise error.DiscussionNodeAlreadyExistError(domain_id, node_name)
    coll = db.Collection('discussion.node')
    await coll.insert_one({'_id': node_name,
                           'name': node_name,
                           'pic': node_pic,
                           'category_name': category_name})


async def check_node(domain_id, node_name):
    if not await get_node(domain_id, node_name):
        raise error.DiscussionNodeNotFoundError(domain_id, node_name)


async def get_nodes_and_vnode(domain_id, node_or_dtuple):
    nodes = await get_nodes(domain_id)
    node = await get_node(domain_id, node_or_dtuple)
    if node:
        vnode = {'type': 'discussion_node', **node}
    elif isinstance(node_or_dtuple, tuple) and node_or_dtuple[0] in ALLOWED_DOC_TYPES:
        # TODO: projection
        coll = db.Collection(node_or_dtuple[0])
        vnode = await coll.find({'domain_id': domain_id,
                                 'type': node_or_dtuple[0],
                                 '_id': node_or_dtuple[1]})
    else:
        vnode = None
    return nodes, vnode


@argmethod.wrap
async def get_vnode(domain_id: str, node_or_dtuple: str):
    _, vnode = await get_nodes_and_vnode(domain_id, node_or_dtuple)
    return vnode


@argmethod.wrap
async def add(domain_id: str, node_or_dtuple: str, owner_uid: int, title: str, content: str, **kwargs):
    validator.check_title(title)
    validator.check_content(content)
    vnode = await get_vnode(domain_id, node_or_dtuple)
    if not vnode:
        raise error.DiscussionNodeNotFoundError(domain_id, node_or_dtuple)
    doc = {'domain_id': domain_id,
           'owner_uid': owner_uid,
           'title': title,
           'content': content,
           'num_replies': 0,
           'num_views': 0,
           'update_at': datetime.datetime.utcnow(),
           'parent_type': vnode['doc_type'],
           'parent_id': vnode['_id'],
           **kwargs}
    coll = db.Collection('discussion')
    await coll.insert_one(doc)


@argmethod.wrap
async def get(domain_id: str, did: objectid.ObjectId):
    coll = db.Collection('discussion')
    return await coll.find_one({'domain_id': domain_id, '_id': did})


@argmethod.wrap
async def edit(domain_id: str, did : objectid.ObjectId, **kwargs):
    coll = db.Collection('discussion')
    return await coll.find_one_and_update(filter={'domain_id': domain_id,
                                                  '_id': did},
                                          update={'$set': kwargs},
                                          return_document=ReturnDocument.AFTER)


@argmethod.wrap
async def delete(domain_id: str, did: objectid.ObjectId):
    # TODO: delete status?
    coll = db.Collection('discussion')
    await coll.delete_one({'domain_id': domain_id,
                           '_id': did})
    coll_reply = db.Collection('discussion.reply')
    await coll_reply.delete_many({'domain_id': domain_id,
                                  'parent_id': did})


@argmethod.wrap
async def inc_views(domain_id: str, did: objectid.ObjectId):
    coll = db.Collection('discussion')
    doc = await coll.find_one_and_update(filter={'domain_id': domain_id,
                                                 '_id': did},
                                         update={'$inc': {'num_views': 1}},
                                         return_document=ReturnDocument.AFTER)
    if not doc:
        raise error.DiscussionNotFoundError(domain_id, did)
    return doc


@argmethod.wrap
async def count(domain_id: str, **kwargs):
    coll = db.Collection('discussion')
    return await coll.find({'domain_id': domain_id, **kwargs}).count()


@argmethod.wrap
def get_multi(domain_id: str, *, projection=None, **kwargs):
    coll = db.Collection('discussion')
    return coll.find({'domain_id': domain_id, **kwargs},
                     projection=projection).sort([('update_at', -1),
                                                  ('_id', -1)])


@argmethod.wrap
async def add_reply(domain_id: str, did: objectid.ObjectId, owner_uid: int, content: str):
    validator.check_content(content)
    coll = db.Collection('discussion')
    coll_reply = db.Collection('discussion.reply')
    drdoc, _ = await asyncio.gather(
        coll_reply.insert_one({'domain_id': domain_id,
                               'content': content,
                               'owner_uid': owner_uid,
                               'parent_type': 'discussion',
                               'parent_id': did}),
        coll.find_one_and_update(filter={'domain_id': domain_id,
                                         '_id': did},
                                 update={'$inc': {'num_replies': 1},
                                         '$set': {'update_at': datetime.datetime.utcnow()}},
                                 return_document=ReturnDocument.AFTER)
    )
    return drdoc


@argmethod.wrap
async def get_reply(domain_id: str, drid: objectid.ObjectId, did=None):
    coll = db.Collection('discussion.reply')
    drdoc = await coll.find_one({'domain_id': domain_id, '_id': drid})
    if not drdoc or (did and drdoc['parent_id'] != did):
        raise error.DocumentNotFoundError(domain_id, drid)
    return drdoc


@argmethod.wrap
async def edit_reply(domain_id: str, drid: objectid.ObjectId, content: str):
    validator.check_content(content)
    coll = db.Collection('discussion.reply')
    return await coll.find_one_and_update(filter={'domain_id': domain_id, '_id': drid},
                                          update={'$set': {'content': content}},
                                          return_document=ReturnDocument.AFTER)


@argmethod.wrap
async def delete_reply(domain_id: str, drid: objectid.ObjectId):
    drdoc = await get_reply(domain_id, drid)
    if not drdoc:
        return None
    coll = db.Collection('discussion')
    coll_reply = db.Collection('discussion.reply')
    await coll_reply.delete_one({'domain_id': domain_id, '_id': drid})
    await coll.find_one_and_update(filter={'domain_id': domain_id,
                                           'parent_type': drdoc['parent_type'],
                                           'parent_id': drdoc['parent_id']},
                                   update={'$inc': {'num_replies': -1}},
                                   return_document=ReturnDocument.AFTER)
    return drdoc


@argmethod.wrap
async def get_list_reply(domain_id: str, did: objectid.ObjectId, *, projection=None):
    coll = db.Collection('discussion.reply')
    return await coll.find({'domain_id': domain_id,
                            'parent_id': did},
                           projection=projection).sort([('_id', -1)]).to_list(None)


def get_multi_reply(domain_id: str, did: objectid.ObjectId, *, projection=None):
    coll = db.Collection('discussion.reply')
    return coll.find({'domain_id': domain_id,
                      'parent_id': did},
                     projection=projection).sort([('_id', -1)])


@argmethod.wrap
async def add_tail_reply(domain_id: str, drid: objectid.ObjectId, owner_uid: int, content: str):
    validator.check_content(content)
    sid = objectid.ObjectId()
    coll = db.Collection('discussion.reply')
    drdoc = await coll.find_one_and_update(filter={'domain_id': domain_id, '_id': drid},
                                           update={'$push': {'reply': {
                                               '_id': sid,
                                               'owner_uid': owner_uid,
                                               'content': content
                                           }}},
                                           return_document=ReturnDocument.AFTER)
    coll = db.Collection('discussion')
    await coll.find_one_and_update(filter={'domain_id': domain_id,
                                           '_id': drdoc['parent_id']},
                                   update={'$set': {'update_at': datetime.datetime.utcnow()}},
                                   return_document=ReturnDocument.AFTER)
    return drdoc, sid


@argmethod.wrap
async def get_tail_reply(domain_id: str, drid: objectid.ObjectId, drrid: objectid.ObjectId):
    coll = db.Collection('discussion.reply')
    doc = await coll.find_one({'domain_id': domain_id,
                               '_id': drid,
                               'reply': {'$elemMatch': {'_id': drrid}}})
    if not doc:
        return None, None
    for sdoc in doc.get('reply', []):
        if sdoc['_id'] == drrid:
            return doc, sdoc
    return doc, None


@argmethod.wrap
async def edit_tail_reply(domain_id: str, drid: objectid.ObjectId, drrid: objectid.ObjectId, content: str):
    coll = db.Collection('discussion.reply')
    doc = await coll.find_one_and_update(filter={'domain_id': domain_id,
                                                 '_id': drid,
                                                 'reply': {'$elemMatch': {'_id': drrid}}},
                                         update={'$set': {'reply.$.content': content}},
                                         return_document=ReturnDocument.AFTER)
    return doc


@argmethod.wrap
async def delete_tail_reply(domain_id: str, drid: objectid.ObjectId, drrid: objectid.ObjectId):
    coll = db.Collection('discussion.reply')
    doc = await coll.find_one_and_update(filter={'domain_id': domain_id,
                                                 '_id': drid},
                                         update={'$pull': {'reply': {'_id': drrid}}},
                                         return_document=ReturnDocument.AFTER)
    return doc


async def get_dict_vnodes(domain_id, node_or_dtuples):
    result = dict()
    dtuples = set()
    for node_or_dtuple in node_or_dtuples:
        if get_node(domain_id, node_or_dtuple):
            result[node_or_dtuple] = {'_id': node_or_dtuple,
                                      'type': 'discussion_node',
                                      'title': node_or_dtuple}
        elif node_or_dtuple[0] in ALLOWED_DOC_TYPES:
            dtuples.add(node_or_dtuple)
    for doc_type, doc_id in dtuples:
        coll = db.Collection(doc_type)
        doc = await coll.find_one({'domain_id': domain_id, '_id': doc_id})
        result[(doc_type, doc_id)] = doc
    return result


@argmethod.wrap
async def set_star(domain_id: str, did: objectid.ObjectId, uid: int, star: bool):
    coll = db.Collection('discussion.status')
    return await coll.find_one_and_update(filter={'domain_id': domain_id,
                                                  '_id': did,
                                                  'uid': uid},
                                          update={'$set': {'star': star}},
                                          upsert=True,
                                          return_document=ReturnDocument.AFTER)


@argmethod.wrap
async def get_status(domain_id: str, did: objectid.ObjectId, uid: int):
    coll = db.Collection('discussion.status')
    return await coll.find_one({'domain_id': domain_id,
                                '_id': did,
                                'uid': uid})


if __name__ == '__main__':
    argmethod.invoke_by_args()
