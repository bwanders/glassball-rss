import argparse
import configparser
import pathlib
import sqlite3

from . import get_resource_string


if __name__ == '__main__':
    args = argparse.ArgumentParser(description='Initialize a glassball configuration')
    args.add_argument('name', nargs='?', default='feeds.ini', help='The name of the configuration and database files')
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

    config = configparser.ConfigParser()
    config.read(ini_file, encoding='utf-8')

    db_file = ini_file.with_name(config['global']['database'])

    if not db_file.exists():
        print("Creating feed item database '{}'...".format(db_file))
        with sqlite3.connect(db_file) as conn:
            schema_source = get_resource_string('schema.sql')
            conn.executescript(schema_source)
    else:
        print("Using existing fedd item database '{}'...".format(db_file))
