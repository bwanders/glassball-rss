import argparse
import contextlib
import sys

from glassball.common import GlassballError, ConfigurationError
from glassball.logging import log_error, log_message, console_log_handler, file_log_handler

import glassball.init
import glassball.list
import glassball.update
import glassball.build
import glassball.rawfeed
import glassball.opmlimport
import glassball.add


command_modules = [
    glassball.init,
    glassball.list,
    glassball.update,
    glassball.build,
    glassball.rawfeed,
    glassball.opmlimport,
    glassball.add,
]


if __name__ == '__main__':
    common_args = argparse.ArgumentParser(add_help=False)
    common_group = common_args.add_argument_group('common arguments')
    common_group.add_argument('-c', '--config', default='feeds.ini', help='The configuration file with which to work')
    common_group.add_argument('-q', '--quiet', action='store_true', help='Prevent and messages and errors from appearing in the output')
    common_group.add_argument('-l', '--log', default=None, help='Log all messages and errors to the given file')

    args = argparse.ArgumentParser(description='RSS/Atom feed tracker and static viewer')

    commands = args.add_subparsers()
    for mod in command_modules:
        mod.register_command(commands, common_args)

    options = args.parse_args()

    command_func = getattr(options, 'command_func', None)
    if not command_func:
        args.print_help()
        args.exit(2)

    # We do this dance with the exit stack to make sure that we close the log
    # file at the appropriate time. The `console_log_handler` is just here for
    # symmetry.
    with contextlib.ExitStack() as stack:
        if not options.quiet:
            stack.enter_context(console_log_handler())
        if options.log:
            stack.enter_context(file_log_handler(options.log))

        try:
            command_func(options)
        except GlassballError as e:
            log_error(str(e), exception=e)
            args.exit(2)
