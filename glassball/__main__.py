import argparse

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
    args = argparse.ArgumentParser(description='RSS/Atom feed tracker and static viewer')
    commands = args.add_subparsers()

    for mod in command_modules:
        mod.register_command(commands)

    options = args.parse_args()

    command_func = getattr(options, 'command_func', None)
    if not command_func:
        args.print_help()
        args.exit(2)

    command_func(options)
