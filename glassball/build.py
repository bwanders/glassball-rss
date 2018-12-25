import argparse
import datetime
import pathlib

import jinja2

from .common import copy_resources, Configuration, GlassballError, db_datetime


item_fields = {
    'id': lambda x: x,
    'feed': lambda x: x,
    'guid': lambda x: x,
    'published': db_datetime,
    'link': lambda x: x,
    'title': lambda x: x,
    'author': lambda x: x,
    'content': lambda x: x,
}


def item_transform(item_row):
    result = {}
    available = item_row.keys()
    for k, f in item_fields.items():
        if k in available:
            result[k] = f(item_row[k])
    return result


def build_site(config, *, overwrite=False):
    env = jinja2.Environment(loader=jinja2.PackageLoader(__name__, 'templates'), autoescape=jinja2.select_autoescape(['html', 'xml']))

    env.filters['datetime'] = lambda value, format='%Y-%m-%d %H:%M:%S': value.strftime(format)

    if not config.build_directory.exists():
        print("Creating build directory '{}'...".format(config.build_directory))
        config.build_directory.mkdir()
    elif config.build_directory.is_dir():
        print("Using existing build directory '{}'...".format(config.build_directory))
    else:
        raise GlassballError("Cannot use build directory '{}'".format(config.build_directory))

    # Copy static files over
    copy_resources('static', config.build_directory / 'static')

    with config.open_database() as conn:
        # First, we render out the index file
        index_template = env.get_template('index.html')
        items = conn.cursor()
        items.execute('SELECT id, feed, title, author, published FROM item ORDER BY published DESC')

        with open(config.build_directory / 'index.html', 'w', encoding='utf-8') as f:
            f.write(index_template.render(feeds=config.feeds, items=map(item_transform, items)))

        item_template = env.get_template('item.html')
        items = conn.cursor()
        items.execute('SELECT id, link, feed, title, author, published, content FROM item')
        for item in items:
            item_file = config.build_directory / "{}.html".format(item['id'])
            if item_file.exists() and not overwrite:
                continue
            with open(item_file, 'w', encoding='utf-8') as f:
                f.write(item_template.render(item=item_transform(item)))



if __name__ == '__main__':
    args = argparse.ArgumentParser(description='Builds a set of static HTML files that can be used to view the feed items')
    args.add_argument('name', nargs='?', default='feeds.ini', help='The name of the configuration file')
    args.add_argument('-f', '--force', action='store_true', help='Force update of existing files by overwriting them')
    options = args.parse_args()

    config = Configuration(options.name)

    build_site(config, overwrite=options.force)
