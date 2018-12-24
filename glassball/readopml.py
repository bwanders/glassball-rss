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


if __name__ == '__main__':
    args = argparse.ArgumentParser(description='Read an OPML file and output a copy-pasteable config')
    args.add_argument('opml', type=argparse.FileType(), help='The OPML file')
    options = args.parse_args()

    config = configparser.ConfigParser(interpolation=None)
    names = set()

    tree = ElementTree.parse(options.opml)
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

    config.write(sys.stdout)
