import argparse
import datetime
import pathlib

import jinja2

from .common import copy_resources, Configuration, CommandError, db_datetime
from .logging import log_error, log_message


def register_command(commands, common_args):
    args = commands.add_parser('build', help='Builds a set of static HTML files that can be used to view the feed items', parents=[common_args])
    args.add_argument('-f', '--force', action='store_true', help='Force update of existing files by overwriting them')
    args.set_defaults(command_func=command_build)


def command_build(options):
    config = Configuration(options.config)
    build_site(config, overwrite=options.force)


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

    if not config.build_path.exists():
        log_message("Creating build directory '{}'...".format(config.build_path))
        config.build_path.mkdir()
    elif config.build_path.is_dir():
        log_message("Using existing build directory '{}'...".format(config.build_path))
    else:
        log_error("Cannot use build directory '{}'".format(config.build_path))
        raise CommandError("Build failed")

    # Copy static files over
    copy_resources('static', config.build_path / 'static')

    with config.open_database() as conn:
        # First, we render out the index file
        index_template = env.get_template('index.html')
        items = conn.cursor()
        items.execute('SELECT id, feed, title, author, published FROM item ORDER BY published DESC')

        c = conn.cursor()
        c.execute('SELECT feed, updated, success FROM last_update')
        last_update = {config.get_feed(feed): {'updated': db_datetime(updated), 'success': success} for feed, updated, success in c.fetchall()}

        with open(config.build_path / 'index.html', 'w', encoding='utf-8') as f:
            f.write(index_template.render(feeds=config.feeds, last_update=last_update, items=map(item_transform, items)))

        item_template = env.get_template('item.html')
        items = conn.cursor()
        items.execute('SELECT id, link, feed, title, author, published, content FROM item')
        for item in items:
            item_file = config.build_path / "{}.html".format(item['id'])
            if item_file.exists() and not overwrite:
                continue
            with open(item_file, 'w', encoding='utf-8') as f:
                f.write(item_template.render(item=item_transform(item)))
