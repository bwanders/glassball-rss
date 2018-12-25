import argparse
import pprint
import textwrap

import feedparser

from .common import Configuration


def register_command(commands):
    args = commands.add_parser('raw-feed', help='Retrieves and dumps a raw feed')
    args.add_argument('url', help='The feed URL')
    args.add_argument('-c', '--config', help='Optional configuration file to use to resolve keys to feed URLs')
    args.add_argument('-a', '--all', action='store_true', help='Output all entry information as well as the feed information')
    args.set_defaults(command_func=command_rawfeed)


def indent_pprint(thing, prefix='    '):
    print(textwrap.indent(pprint.pformat(thing), prefix))


def command_rawfeed(options):
    # If we are given a config, we can try to look up a non-URL parameter
    # against the feeds in the config
    if options.config:
        config = Configuration(options.config)
        if not options.url.startswith('http'):
            feed = config.get_feed(options.url)
            if feed:
                options.url = feed.url

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
