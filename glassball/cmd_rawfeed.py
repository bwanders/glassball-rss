import argparse
import pprint
import textwrap

import feedparser

from .common import Configuration, CommandError
from .logging import log_error, log_message


def register_command(commands, common_args):
    args = commands.add_parser('raw-feed', help='Retrieves and dumps a raw feed', parents=[common_args])
    args.add_argument('url', help='The feed URL')
    args.add_argument('-a', '--all', action='store_true', help='Output all entry information as well as the feed information')
    args.set_defaults(command_func=command_rawfeed)


def command_rawfeed(options):
    # Helper to do an indented pretty print
    def indent_pprint(thing, prefix='    '):
        print(textwrap.indent(pprint.pformat(thing), prefix))

    # This is completely opinionated: anything not starting with `http` is not
    # retrievable...
    if not options.url.startswith('http'):
        # If we are given a config, we can try to look up a non-URL parameter
        # against the feeds in the config
        if Configuration.exists(options.config):
            config = Configuration(options.config)
            feed = config.get_feed(options.url)
            if feed:
                options.url = feed.url
            else:
                raise CommandError("Cannot translate name '{}' to a feed URL with '{}'".format(options.url, options.config))
        else:
            raise CommandError("Given url '{}' does not seem to be a retrievable URL".format(options.url))

    # Proceed to retrieve the feed
    feed = feedparser.parse(options.url)

    display_keys = set(feed.keys()) - {'entries'}

    first = True
    for key in sorted(display_keys):
        if not first:
            print()
        first = False
        print("{}:".format(key))
        indent_pprint(feed[key])

    if options.all:
        for entry in feed.entries:
            print()
            print("Article:")
            indent_pprint(entry)
