import argparse
import configparser
import pathlib
import re
import sys

from xml.etree import ElementTree

from .common import Configuration
from .logging import log_error, log_message


def slugify(s):
    s = str(s).lower()
    s = re.sub('[^a-z0-9-_]+', '-', s)
    s = s.strip('-')
    return s


def register_command(commands, common_args):
    args = commands.add_parser('import', help='Read an OPML file and output a copy-pasteable config', parents=[common_args], epilog="If the configuration file can be loaded, imported feeds that have the same URL as an already configured feed will be skipped.")
    args.add_argument('opml', type=argparse.FileType(), help='An OPML file to process')
    args.add_argument('-a', '--all', action='store_true', help='Output all feeds regardless of presence in current configuration')
    args.set_defaults(command_func=command_import_opml)


def command_import_opml(options):
    known_urls = set()
    if Configuration.exists(options.config):
        config = Configuration(options.config)
        known_urls = {feed.url for feed in config.feeds}

    feeds = read_opml(options.opml, initial_names={feed.key for feed in config.feeds})
    result = configparser.ConfigParser(interpolation=None)
    for feed, settings in feeds.items():
        if settings['url'] in known_urls and not options.all:
            continue
        result[feed] = {}
        result[feed]['url'] = settings['url']
        result[feed]['title'] = settings['title']
    result.write(sys.stdout)


def read_opml(opml_file, initial_names=()):
    result = {}
    names = set(initial_names)

    tree = ElementTree.parse(opml_file)
    for node in tree.findall('.//outline'):
        url = node.attrib.get('xmlUrl')
        if not url:
            continue
        text = node.attrib.get('text')
        if not text:
            text = 'unnamed-' + len(names)
        name = candidate_name = slugify(text)
        i = 1
        while name in names:
            i += 1
            name = "{}--{}".format(candidate_name, i)
        names.add(name)
        key = 'feed:' + name
        result[key] = {}
        result[key]['url'] = str(url)
        result[key]['title'] = text
    return result