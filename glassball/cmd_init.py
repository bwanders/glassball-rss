import pathlib
import uuid

import jinja2

from .common import get_resource_string, open_database, Configuration
from .logging import log_error, log_message
from .cmd_opmlimport import read_opml


def register_command(commands, common_args):
    args = commands.add_parser('init', help='Intialize a glassball configuration and database', parents=[common_args])
    args.add_argument('--import', dest='import_opml', default=None, help='An optional OPML-file to import into the created configuration')
    args.set_defaults(command_func=command_init)


def command_init(options):
    ini_file = pathlib.Path(options.config)

    # Set up configuration file if necessary
    if not ini_file.exists():
        env = jinja2.Environment(loader=jinja2.PackageLoader(__name__, 'templates'))

        log_message("Creating template configuration file '{}'...".format(ini_file))
        with open(ini_file, 'w', encoding='utf-8') as config:
            # Determine expected paths
            expected_db_path = pathlib.Path(ini_file.stem + '.db')
            expected_build_path = 'build'
            # Get imported feeds, if requested
            import_file = None
            import_feeds = None
            if options.import_opml:
                import_file = options.import_opml
                import_feeds = read_opml(options.import_opml)
            # Render out configuration template
            config_template = env.get_template('configuration.ini')
            config.write(config_template.render(database_file=str(expected_db_path), build_path=str(expected_build_path), import_file=import_file, import_feeds=import_feeds))
    else:
        log_message("Using existing configuration file '{}'...".format(ini_file))

    # Read in configuration
    config = Configuration(ini_file)

    # Set up database file if necessary
    if not config.database_file.exists():
        log_message("Creating feed item database '{}'...".format(config.database_file))
        with open_database(config.database_file) as conn:
            schema_source = get_resource_string('schema.sql')
            conn.executescript(schema_source)
            conn.execute("INSERT INTO database_id VALUES(?)", (str(uuid.uuid4()),))
    else:
        log_message("Using existing feed item database '{}'...".format(config.database_file))
