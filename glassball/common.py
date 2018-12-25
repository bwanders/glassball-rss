import configparser
import datetime
import os.path
import pathlib
import pkg_resources
import sqlite3


class GlassballError(Exception):
    pass


_res_manager = pkg_resources.ResourceManager()
_res_provider = pkg_resources.get_provider(__name__)

def get_resource_string(path):
    return _res_provider.get_resource_string(_res_manager, path).decode('utf-8')


def copy_resources(resource, target_path):
    if pkg_resources.resource_isdir(__name__, resource):
        for entry in pkg_resources.resource_listdir(__name__, resource):
            if not target_path.exists():
                target_path.mkdir()
            elif not target_path.is_dir():
                raise GlassballError("Cannot create target path '{}' for copied resource".format(target_path))
            copy_resources(os.path.join(resource, entry), target_path / entry)
    else:
        with open(target_path, 'wb') as f:
            f.write(pkg_resources.resource_string(__name__, resource))


def open_database(db_file):
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn


def db_datetime(value):
    return datetime.datetime(*map(int, value.replace(' ', '-').replace(':','-').split('-')))


_units = ['week', 'day', 'hour', 'minute', 'second']
_plural_units = [u + 's' for u in _units]
_normalize_units = {k: v for k, v in zip(_units, _plural_units)}

def parse_update_interval(user_input):
    arguments = {}

    parts = user_input.replace(',',' ').split()
    if len(parts) % 2 != 0:
        raise GlassballError("Cannot parse duration {!r}".format(user_input))

    pairs = iter(parts)
    for amount, unit in zip(pairs, pairs):
        user_unit = unit
        unit = _normalize_units.get(unit, unit)
        if unit not in _plural_units:
            raise GlassballError("Unkown duration unit {!r} in {!r}".format(user_unit, user_input))
        try:
            arguments[unit] = int(amount)
        except ValueError as e:
            raise GlassballError("Cannot convert amount {!r} to a number for the {!r} part of {!r}".format(amount, user_unit, user_input))

    return datetime.timedelta(**arguments)


class Feed:
    def __init__(self, key, title, url, update_interval, accept_bozo):
        self.key = key
        self.title = title
        self.url = url
        self.update_interval = update_interval
        self.accept_bozo = accept_bozo


class Configuration:
    def __init__(self, ini_file):
        self.configuration_file = pathlib.Path(ini_file)

        self._config = configparser.ConfigParser()
        self._config.read(self.configuration_file, encoding='utf-8')

        self.database_file = self.configuration_file.with_name(self._config['global']['database'])
        self._database_conn = None

        self.build_path = self.configuration_file.with_name(self._config['global']['build path'])

        self.feeds = []
        for section in self._config.sections():
            if not section.startswith('feed:'):
                continue
            key = section[5:]
            title = self._config.get(section, 'title', fallback=key)
            url = self._config.get(section, 'url')
            update_interval = self._config.get(section, 'update interval', fallback='1 second')
            accept_bozo = self._config.getboolean(section, 'accept bozo data', fallback='false')
            self.feeds.append(Feed(key, title, url, parse_update_interval(update_interval), accept_bozo))

    def open_database(self):
        if not self.database_file.exists():
            raise GlassballError("Database file '{}' does not exists".format(self.database_file))
        return open_database(self.database_file)
