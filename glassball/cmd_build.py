import datetime

import jinja2

from .common import copy_resources, Configuration, GlassballError, db_datetime, log_error, log_message


class BuildError(GlassballError):
    pass


def register_command(commands, common_args):
    args = commands.add_parser('build', help='Builds a set of static HTML files that can be used to view the feed items', parents=[common_args])
    args.add_argument('-f', '--force', action='store_true', help='Force update of existing item files by overwriting them')
    args.set_defaults(command_func=command_build)


def command_build(options):
    config = Configuration(options.config)
    build_site(config, overwrite=options.force)


def build_site(config, *, overwrite=False):
    # Set up jinja2 environment
    env = jinja2.Environment(loader=jinja2.PackageLoader(__name__, 'templates'), autoescape=jinja2.select_autoescape(['html', 'xml']))

    # Template filter for displays of datetime instances
    env.filters['datetime'] = lambda value, format='%Y-%m-%d %H:%M:%S': value.strftime(format)

    # Templater filter for "X time ago" displays of datetime instances
    def format_ago(value):
        delta = datetime.datetime.now() - value
        return value.strftime('%H:%M') if delta.days == 0 else value.strftime('%Y-%m-%d')
    env.filters['ago'] = format_ago

    # Feed item field converters to go from database to in-memory
    item_fields = {
        'id': lambda x: x,
        'feed': lambda x: config.get_feed(x),
        'guid': lambda x: x,
        'published': db_datetime,
        'link': lambda x: x,
        'title': lambda x: x,
        'author': lambda x: x,
        'content': lambda x: x,
    }

    # Transformation function to apply item field converters
    def item_transform(row):
        available = row.keys()
        return {k: f(row[k]) for k,f in item_fields.items() if k in available}

    # Ensure availability of build path
    if not config.build_path.exists():
        log_message("Creating build directory '{}'...".format(config.build_path))
        config.build_path.mkdir()
    elif config.build_path.is_dir():
        # We are fine with using an existing build directory
        pass
    else:
        log_error("Cannot use build directory '{}'".format(config.build_path))
        raise BuildError("Build failed")

    # Copy static files over
    copy_resources('static', config.build_path / 'static')

    with config.open_database() as conn:
        # 1: Render out the index file
        index_template = env.get_template('index.html')
        items = conn.cursor()
        items.execute('SELECT id, feed, title, author, published FROM item ORDER BY published DESC')

        c = conn.cursor()
        c.execute('SELECT id from database_id')
        database_id = c.fetchone()['id']

        c.execute('SELECT feed, updated, success FROM last_update')
        last_update = {config.get_feed(feed): {'updated': db_datetime(updated), 'success': success} for feed, updated, success in c.fetchall()}

        with open(config.build_path / 'index.html', 'w', encoding='utf-8') as f:
            f.write(index_template.render(database_id=database_id, feeds=config.feeds, last_update=last_update, items=map(item_transform, items)))

        # 2: Ensure availability of `items` directory under build path
        item_path = config.build_path / 'items'
        if not item_path.exists():
            item_path.mkdir()

        # 3: Render out an item file for each item
        item_template = env.get_template('item.html')
        items = conn.cursor()
        items.execute('SELECT id, link, feed, title, author, published, content FROM item')
        for item in items:
            item = item_transform(item)
            feed = item['feed']
            # Determine item file and skip out if we do not need to render it
            item_file = item_path / "{}.html".format(item['id'])
            if item_file.exists() and not overwrite:
                continue
            # Prepare for rendering
            injected_styling = None
            if feed and feed.inject_style_file:
                injected_styling = config.relative_path(feed.inject_style_file).read_text(encoding='utf-8')
            # Render the actual item
            with open(item_file, 'w', encoding='utf-8') as f:
                f.write(item_template.render(feed=feed, item=item, injected_styling=injected_styling))
