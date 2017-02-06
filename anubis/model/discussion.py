import asyncio
import collections
import datetime
from bson import objectid
from pymongo import errors

from anubis import error
from anubis.service import smallcache
from anubis.util import argmethod
from anubis.util import validator


def node_id(ddoc):
    if ddoc['parent_doc_']
