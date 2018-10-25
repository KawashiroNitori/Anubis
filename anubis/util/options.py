import argparse
import os
import sys

_parser = argparse.ArgumentParser()
options = argparse.Namespace()
leftovers = sys.argv[1:]


def define(name: str, default=None, help=None):
    flag_name = '--' + name.replace('_', '-')
    flag_type = type(default)
    env_name = name.upper()
    env_value = os.environ.get(env_name)
    if flag_type is bool:
        if env_value is not None:
            default = True
        _parser.add_argument(flag_name, dest=name, action='store_true', help=help)
        _parser.add_argument('--no-' + name.replace('_', '-'), dest=name, action='store_false')
        _parser.set_defaults(**{name: default})
    else:
        if env_value is not None:
            default = flag_type(env_value)
        _parser.add_argument(flag_name, dest=name, default=default, type=flag_type, help=help)
    global leftovers
    _, leftovers = _parser.parse_known_args(args=sys.argv[1:], namespace=options)
