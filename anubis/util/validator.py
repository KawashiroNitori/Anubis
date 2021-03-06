import re

from anubis import constant
from anubis import error


def is_uid(s):
    return bool(re.fullmatch(r'-?\d+', s))


def check_uid(s):
    if not is_uid(s):
        raise error.ValidationError('uid')


def is_uname(s):
    return bool(re.fullmatch(r'[^\s\u3000](.{,16}[^\s\u3000])?', s))


def check_uname(s):
    if not is_uname(s):
        raise error.ValidationError('uname')


def is_password(s):
    return bool(re.fullmatch(r'.{5,}', s))


def check_password(s):
    if not is_password(s):
        raise error.ValidationError('password')


def is_mail(s):
    return bool(re.fullmatch(r'\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*', s))


def check_mail(s):
    if not is_mail(s):
        raise error.ValidationError('mail')


def check_time_second_limit(s):
    if s < 1 or s > 10:
        raise error.ValidationError('time')


def check_memory_mb_limit(s):
    if s < 32 or s > 1024:
        raise error.ValidationError('memory')


def is_domain_id(s):
    return bool(re.fullmatch(r'[^0-9\\/\s\u3000][^\\/\n\r]{2,}[^\\/\s\u30000]', s))


def check_domain_id(s):
    if not is_domain_id(s):
        raise error.ValidationError('domain_id')


def is_campaign_id(s):
    return bool(re.fullmatch(r'\w{7,}', s))


def check_campaign_id(s):
    if not is_campaign_id(s):
        raise error.ValidationError('campaign_id')


def is_id(s):
    return bool(re.fullmatch(r'[^\\/\s\u3000]([^\\/\n\r]*[^\\/\s\u3000])?', s))


def check_category_name(s):
    if not is_id(s):
        raise error.ValidationError('category_name')


def check_node_name(s):
    if not is_id(s):
        raise error.ValidationError('node_name')


def is_role(s):
    return bool(re.fullmatch(r'[_0-9A-Za-z]+', s))


def check_role(s):
    if not is_role(s):
        raise error.ValidationError('role')


def is_title(s):
    return bool(re.fullmatch(r'.{1,}', s))


def check_title(s):
    if not is_title(s):
        raise error.ValidationError('title')


def is_name(s):
    return bool(re.fullmatch(r'.{1,}', s))


def check_name(s):
    if not is_name(s):
        raise error.ValidationError('name')


def is_content(s):
    return isinstance(s, str) and len(str(s).strip()) >= 2


def check_content(s):
    if not is_content(s):
        raise error.ValidationError('content')


def is_description(s):
    return isinstance(s, str)


def check_description(s):
    if not is_description(s):
        raise error.ValidationError('description')


def is_lang(s):
    return s in constant.language.LANG_TEXTS


def check_lang(s):
    if not is_lang(s):
        raise error.ValidationError('lang')


def is_tel(s):
    return bool(re.fullmatch(r'^1(3|4|5|7|8)[0-9]\d{8}$', s))


def check_tel(s):
    if not is_tel(s):
        raise error.ValidationError('tel')


def is_team_name(s):
    return bool(re.fullmatch(r'^[a-zA-Z0-9\u4e00-\u9fa5][a-zA-Z0-9 \u4e00-\u9fa5]{1,8}[a-zA-Z0-9\u4e00-\u9fa5]$', s))


def check_team_name(s):
    if not is_team_name(s):
        raise error.ValidationError('team_name')
