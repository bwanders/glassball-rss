import argparse
import configparser
import sys

import feedparser

from .common import Configuration, CommandError, slugify, find_free_name
from .logging import log_error, log_message


def register_command(commands, common_args):
    args = commands.add_parser('add', help='Retrieves a feed URL and produces a copy-pastable configuration snippet', parents=[common_args])
    args.add_argument('url', help='The feed URL to retrieve')
    args.add_argument('-f', '--force', action='store_true', help='Force snippet creation even if the URL is already configured')
    args.set_defaults(command_func=command_add)


def command_add(options):
    known_urls = {}
    names = set()
    if Configuration.exists(options.config):
        config = Configuration(options.config)
        names = {feed.key for feed in config.feeds}
        for feed in config.feeds:
            known_urls.setdefault(feed.url, [])
            known_urls[feed.url].append(feed)

    if options.url in known_urls and not options.force:
        print("The feed URL '{}' is already configured as {}".format(options.url, ", ".join(repr(feed.key) for feed in known_urls[options.url])))
        return

    feed = feedparser.parse(options.url)
    if feed.bozo:
        print("Cannot add feed: the feed at '{}' is unretrievable, malformed, or otherwise not in good shape.".format(options.url))
        return

    title = feed.feed.title

    name = find_free_name(slugify(title), names)
    names.add(name)
    key = 'feed:' + name

    result = configparser.ConfigParser(interpolation=None)
    result[key] = {}
    result[key]['url'] = options.url
    result[key]['title'] = title
    result.write(sys.stdout)
