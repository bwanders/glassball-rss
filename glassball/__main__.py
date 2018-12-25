import argparse

from glassball.common import GlassballError

import glassball.init
import glassball.list
import glassball.update
import glassball.build
import glassball.rawfeed
import glassball.readopml


command_modules = [
    glassball.init,
    glassball.list,
    glassball.update,
    glassball.build,
    glassball.rawfeed,
    glassball.readopml,
]


if __name__ == '__main__':
    common_args = argparse.ArgumentParser(add_help=False)
    common_group = common_args.add_argument_group('common arguments')
    common_group.add_argument('-c', '--config', default='feeds.ini', help='The configuration file with which to work')

    args = argparse.ArgumentParser(description='RSS/Atom feed tracker and static viewer')

    commands = args.add_subparsers()
    for mod in command_modules:
        mod.register_command(commands, common_args)

    options = args.parse_args()

    command_func = getattr(options, 'command_func', None)
    if not command_func:
        args.print_help()
        args.exit(2)

    try:
        command_func(options)
    except GlassballError as e:
        args.error(str(e))
