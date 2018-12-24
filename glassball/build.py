import argparse
import pathlib

import jinja2

from .common import copy_resources, Configuration, GlassballError


def build_site(config):
    env = jinja2.Environment(loader=jinja2.PackageLoader(__name__, 'templates'), autoescape=jinja2.select_autoescape(['html', 'xml']))

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
        feeds = config.feeds
        items = conn.cursor()
        items.execute('SELECT id, feed, title, author, published FROM item ORDER BY published DESC')
        index_template = env.get_template('index.html')
        with open(config.build_directory / 'index.html', 'w', encoding='utf-8') as f:
            f.write(index_template.render(feeds=feeds, items=items))



if __name__ == '__main__':
    args = argparse.ArgumentParser(description='Builds a set of static HTML files that can be used to view the feed items')
    args.add_argument('name', nargs='?', default='feeds.ini', help='The name of the configuration file')
    options = args.parse_args()

    config = Configuration(options.name)

    build_site(config)
