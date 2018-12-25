import configparser
import datetime
import os.path
import pathlib
import pkg_resources
import sqlite3


class GlassballError(Exception):
    pass


class CommandError(GlassballError):
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
        raise ValueError("Cannot parse duration {!r}".format(user_input))

    pairs = iter(parts)
    for amount, unit in zip(pairs, pairs):
        user_unit = unit
        unit = _normalize_units.get(unit, unit)
        if unit not in _plural_units:
            raise ValueError("Unkown duration unit {!r} in {!r}".format(user_unit, user_input))
        try:
            arguments[unit] = int(amount)
        except ValueError as e:
            raise ValueError("Cannot convert amount {!r} to a number for the {!r} part of {!r}".format(amount, user_unit, user_input)) from e

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

        if not self.configuration_file.exists():
            raise GlassballError("Configuration file {!r} does not exists".format(str(self.configuration_file)))

        self._config = configparser.ConfigParser()
        try:
            self._config.read([str(self.configuration_file)], encoding='utf-8')
        except configparser.Error as e:
            raise GlassballError(str(e)) from e

        try:
            self.database_file = self.configuration_file.with_name(self._config.get('global', 'database'))
            self._database_conn = None
        except configparser.NoOptionError as e:
            raise GlassballError("Configuration {!r} lacks database file entry: {}".format(str(self.configuration_file), e)) from e

        self._feeds = {}
        for section in self._config.sections():
            if not section.startswith('feed:'):
                continue
            key = section[5:]
            try:
                title = self._config.get(section, 'title', fallback=key)
                url = self._config.get(section, 'url')
                update_interval = self._config.get(section, 'update interval', fallback='1 hour')
                accept_bozo = self._config.getboolean(section, 'accept bozo data', fallback='false')
            except configparser.Error as e:
                raise GlassballError("Misconfiguration feed in {!r}: {}".format(str(self.configuration_file), e)) from e
            try:
                update_interval = parse_update_interval(update_interval)
            except ValueError as e:
                raise GlassballError("Cannot understand update interval {!r} for feed {!r} in {!r}".format(update_interval, section, str(self.configuration_file)))
            self._feeds[key] = Feed(key, title, url, update_interval, accept_bozo)

    @classmethod
    def exists(cls, ini_file):
        return pathlib.Path(ini_file).exists()

    @property
    def feeds(self):
        return list(self._feeds.values())

    @property
    def build_path(self):
        try:
            return self.configuration_file.with_name(self._config.get('global', 'build path'))
        except configparser.NoOptionError as e:
            raise GlassballError("Missing build path in {!r}: {}".format(str(self.configuration_file), e))

    def get_feed(self, key):
        return self._feeds.get(key)

    def open_database(self):
        if not self.database_file.exists():
            raise GlassballError("Database file '{}' does not exists".format(str(self.database_file)))
        return open_database(self.database_file)
