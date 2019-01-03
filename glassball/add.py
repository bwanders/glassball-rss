import configparser
import sys

import feedparser

from .common import Configuration, CommandError, slugify, find_free_name
from .logging import log_error, log_message


def register_command(commands, common_args):
    args = commands.add_parser('add', help='Retrieves a feed URL and produces a copy-pastable configuration snippet', parents=[common_args])
    args.add_argument('url', help='The feed URL to retrieve')
    args.add_argument('-f', '--force', action='store_true', help='Force snippet creation even if the URL is already configured')
    args.add_argument('-w', '--write-config', action='store_true', help='Writes the import feeds directly to the configuration')
    args.set_defaults(command_func=command_add)


def command_add(options):
    # Already known feed URLs and names
    known_urls = {}
    known_names = set()

    # If we can use the given configuration we update the known URLs and names
    if Configuration.exists(options.config):
        config = Configuration(options.config)
        known_names = {feed.key for feed in config.feeds}
        for feed in config.feeds:
            known_urls.setdefault(feed.url, [])
            known_urls[feed.url].append(feed)

    # Prevent double registrations during normal operations
    if options.url in known_urls and not options.force:
        print("The feed URL '{}' is already configured as {}".format(options.url, ", ".join(repr(feed.key) for feed in known_urls[options.url])))
        return

    # Retrieve feed content
    feed = feedparser.parse(options.url)
    if feed.bozo:
        print("Cannot add feed: the feed at '{}' is unretrievable, malformed, or otherwise not in good shape.".format(options.url))
        return

    # Get necessary information from retrieved feed
    title = feed.feed.get('title', 'untitled')

    name = find_free_name(slugify(title), known_names)
    known_names.add(name)
    key = 'feed:' + name

    # Set up configuration snippet for output
    result = configparser.ConfigParser(interpolation=None)
    result[key] = {}
    result[key]['url'] = options.url
    result[key]['title'] = title

    # Write out snippet to requested target
    if options.write_config:
        if not Configuration.exists(options.config):
            raise CommandError("Cannot update configuration '{}' with added feed: configuration does not exist".format(options.config))
        with open(options.config, 'a', encoding='utf-8') as f:
            print(file=f)
            result.write(f)
    else:
        result.write(sys.stdout)
