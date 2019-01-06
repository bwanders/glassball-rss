import argparse
import configparser
import pathlib
import sys

from xml.etree import ElementTree

from .common import Configuration, slugify, find_free_name, CommandError, log_error, log_message


def register_command(commands, common_args):
    args = commands.add_parser('import', help='Read an OPML file and output a copy-pasteable config', parents=[common_args], epilog="If the configuration file can be loaded, imported feeds that have the same URL as an already configured feed will be skipped.")
    args.add_argument('opml', type=argparse.FileType(), help='An OPML file to process')
    args.add_argument('-f', '--force', action='store_true', help='Output all feeds regardless of presence in current configuration')
    args.add_argument('-w', '--write-config', action='store_true', help='Writes the import feeds directly to the configuration')
    args.set_defaults(command_func=command_import_opml)


def command_import_opml(options):
    # Already known feed URLs and names
    known_urls = set()
    known_names = set()
    # If we can use the given configuration we update the known URLs and names
    if Configuration.exists(options.config):
        config = Configuration(options.config)
        known_names = {feed.key for feed in config.feeds}
        known_urls = {feed.url for feed in config.feeds}

    # Read the OPML file to get a list of prepared new feeds
    feeds = read_opml(options.opml, known_names=known_names)

    # Set up configuration snippet
    result = configparser.ConfigParser(interpolation=None)
    for feed, settings in feeds.items():
        # Skip the feed if we already know the URL
        if settings['url'] in known_urls and not options.force:
            continue
        result[feed] = {}
        result[feed]['url'] = settings['url']
        result[feed]['title'] = settings['title']

    # Write out the configuration snippet to the requested location
    if options.write_config:
        if not Configuration.exists(options.config):
            raise CommandError("Cannot update configuration '{}' with imported feeds: configuration does not exist".format(options.config))
        with open(options.config, 'a', encoding='utf-8') as f:
            print(file=f)
            result.write(f)
    else:
        result.write(sys.stdout)


def read_opml(opml_file, known_names=()):
    # Set of currently used names
    names = set(known_names)

    # Result dictionary
    result = {}

    # Read the OPML file into an XML tree
    tree = ElementTree.parse(opml_file)
    # Get all the outline elements from the tree
    for node in tree.findall('.//outline'):
        # Get the outline's url or skip this node
        url = node.attrib.get('xmlUrl')
        if not url:
            continue
        # Get the outline's text or
        text = node.attrib.get('text', 'unnamed-' + str(len(names)))
        # Determine the new feed's name
        name = find_free_name(slugify(text), names)
        names.add(name)
        key = 'feed:' + name
        # Add the feed information to the result
        result[key] = {}
        result[key]['url'] = str(url)
        result[key]['title'] = text
    return result
