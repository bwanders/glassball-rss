import argparse
import configparser
import pathlib
import re
import sys

from xml.etree import ElementTree

from .logging import log_error, log_message


def slugify(s):
    s = str(s).lower()
    s = re.sub('[^a-z0-9-_]+', '-', s)
    s = s.strip('-')
    return s


def register_command(commands, common_args):
    args = commands.add_parser('readopml', help='Read an OPML file and output a copy-pasteable config')
    args.add_argument('opml', type=argparse.FileType(), help='The OPML file')
    args.set_defaults(command_func=command_readopml)


def command_readopml(options):
    feeds = read_opml(options.opml)
    config = configparser.ConfigParser(interpolation=None)
    for feed, settings in feeds.items():
        config[feed] = {}
        config[feed]['url'] = settings['url']
        config[feed]['title'] = settings['title']
    config.write(sys.stdout)


def read_opml(opml_file):
    result = {}
    names = set()

    tree = ElementTree.parse(opml_file)
    for node in tree.findall('.//outline'):
        url = node.attrib.get('xmlUrl')
        if not url:
            continue
        text = node.attrib.get('text')
        if not text:
            text = 'unnamed-' + len(names)
        name = candidate_name = slugify(text)
        i = 0
        while name in names:
            i += 1
            name = "{}:{}".format(candidate_name, i)
        names.add(name)
        key = 'feed:' + name
        result[key] = {}
        result[key]['url'] = str(url)
        result[key]['title'] = text
    return result
