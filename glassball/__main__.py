import argparse
import atexit
import sys

from glassball.common import GlassballError, ConfigurationError
from glassball.logging import log_error, log_message, log_handlers

import glassball.cmd_init
import glassball.cmd_list
import glassball.cmd_update
import glassball.cmd_build
import glassball.cmd_rawfeed
import glassball.cmd_opmlimport
import glassball.cmd_add


# An explicit list of modules for which we should register commands. These
# modules should expose a `register_command(sps, ca)` function that receives a
# subparsers instance and a common arguments parser.
command_modules = [
    glassball.cmd_init,
    glassball.cmd_list,
    glassball.cmd_update,
    glassball.cmd_build,
    glassball.cmd_rawfeed,
    glassball.cmd_opmlimport,
    glassball.cmd_add,
]


if __name__ == '__main__':
    # Set up common arguments
    common_args = argparse.ArgumentParser(add_help=False)
    common_group = common_args.add_argument_group('common arguments')
    common_group.add_argument('-c', '--config', default='feeds.ini', help='The configuration file with which to work')
    common_group.add_argument('-q', '--quiet', action='store_true', help='Prevent and messages and errors from appearing in the output')
    common_group.add_argument('-l', '--log', default=None, help='Log all messages and errors to the given file')

    # Construct the "root" argument parser, add each command we know about to
    # it, and parse the arguments
    args = argparse.ArgumentParser(description='RSS/Atom feed tracker and static viewer')
    commands = args.add_subparsers()
    for mod in command_modules:
        mod.register_command(commands, common_args)
    options = args.parse_args()

    # Determine command function to invoke or error out
    command_func = getattr(options, 'command_func', None)
    if not command_func:
        args.print_help()
        args.exit(2)

    # Set up logging as requested
    if not options.quiet:
        log_handlers.append(print)

    if options.log:
        log_file = open(options.log, 'a', encoding='utf', buffering=1)
        atexit.register(log_file.close)
        log_handlers.append(lambda e: print(e, file=log_file))

    # With all set-up done, run the command function and handle errors
    try:
        command_func(options)
    except GlassballError as e:
        log_error(str(e), exception=e)
        args.exit(2)
