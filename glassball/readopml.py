import argparse
import configparser
import pathlib
import re
import sys

from xml.etree import ElementTree


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
    config = readopml(options.opml)
    config.write(sys.stdout)


def readopml(opml_file):
    config = configparser.ConfigParser(interpolation=None)
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
        config['feed:' + name] = {}
        config['feed:' + name]['url'] = str(url)
        config['feed:' + name]['title'] = text
    return config
