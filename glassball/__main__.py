import argparse
import sys

from glassball.common import GlassballError, ConfigurationError
from glassball.logging import log_error, log_message, push_log_handler

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
    common_group.add_argument('-q', '--quiet', action='store_true', help='Suppress any non-output messages and errors from appearing in the output')
    common_group.add_argument('-l', '--logging', action='store_true', help='Force logging to file, even if running in an interactive shell')

    args = argparse.ArgumentParser(description='RSS/Atom feed tracker and static viewer')

    commands = args.add_subparsers()
    for mod in command_modules:
        mod.register_command(commands, common_args)

    options = args.parse_args()
    options.want_file_log = not sys.stdout.isatty() or options.logging
    options.want_console_log = sys.stdout.isatty() and not options.quiet

    command_func = getattr(options, 'command_func', None)
    if not command_func:
        args.print_help()
        args.exit(2)

    if options.want_console_log:
        push_log_handler(print)

    try:
        command_func(options)
    except GlassballError as e:
        log_error(str(e), exception=e)
        args.exit(2)
