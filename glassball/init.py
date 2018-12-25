import argparse
import pathlib

import jinja2

from .common import get_resource_string, open_database, Configuration
from .readopml import readopml


def register_command(commands, common_args):
    args = commands.add_parser('init', help='Intialize a glassball configuration and database', parents=[common_args])
    args.add_argument('--import-opml', help='An optional OPML-file to import into the created configuration')
    args.set_defaults(command_func=command_init)


def command_init(options):
    ini_file = pathlib.Path(options.config)

    if not ini_file.exists():
        env = jinja2.Environment(loader=jinja2.PackageLoader(__name__, 'templates'))

        print("Creating template configuration file '{}'...".format(ini_file))
        with open(ini_file, 'w', encoding='utf-8') as config:
            expected_db_path = pathlib.Path(ini_file.stem + '.db')
            expected_build_path = 'feedviewer'

            imported_feeds = None
            if getattr(options, 'import_opml', None):
                from io import StringIO
                buf = StringIO()
                readopml(options.import_opml).write(buf)
                imported_feeds = buf.getvalue()

            config_template = env.get_template('feeds.ini')
            config.write(config_template.render(database_file=str(expected_db_path), build_path=str(expected_build_path), opml_file=getattr(options, 'import_opml', None), imported_feeds=imported_feeds))
    else:
        print("Using existing configuration file '{}'...".format(ini_file))

    config = Configuration(ini_file)

    if not config.database_file.exists():
        print("Creating feed item database '{}'...".format(config.database_file))
        with open_database(config.database_file) as conn:
            schema_source = get_resource_string('schema.sql')
            conn.executescript(schema_source)
    else:
        print("Using existing feed item database '{}'...".format(config.database_file))
