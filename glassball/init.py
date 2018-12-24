import argparse
import pathlib

from .common import get_resource_string, open_database, Configuration


if __name__ == '__main__':
    args = argparse.ArgumentParser(description='Initialize a glassball configuration and database')
    args.add_argument('name', nargs='?', default='feeds.ini', help='The name of the configuration file')
    options = args.parse_args()

    ini_file = pathlib.Path(options.name)

    if not ini_file.exists():
        print("Creating template configuration file '{}'...".format(ini_file))
        with open(ini_file, 'w', encoding='utf-8') as config:
            expected_db_path = pathlib.Path(ini_file.stem + '.db')
            config_source = get_resource_string('template-config.ini').format(database_file=str(expected_db_path))
            config.write(config_source)
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
