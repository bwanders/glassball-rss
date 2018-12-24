import configparser
import pathlib
import pkg_resources
import sqlite3


class GlassballError(Exception):
    pass


_res_manager = pkg_resources.ResourceManager()
_res_provider = pkg_resources.get_provider(__name__)

def get_resource_string(path):
    return _res_provider.get_resource_string(_res_manager, path).decode('utf-8')


def open_database(db_file):
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn


class Feed:
    def __init__(self, key, title, url):
        self.key = key
        self.title = title
        self.url = url


class Configuration:
    def __init__(self, ini_file):
        self.configuration_file = pathlib.Path(ini_file)

        self._config = configparser.ConfigParser()
        self._config.read(self.configuration_file, encoding='utf-8')

        self.database_file = self.configuration_file.with_name(self._config['global']['database'])
        self._database_conn = None

        self.feeds = []
        for section in self._config.sections():
            if not section.startswith('feed:'):
                continue
            key = section[5:]
            title = self._config.get(section, 'title', fallback=key)
            url = self._config.get(section, 'url')
            self.feeds.append(Feed(key, title, url))

    def open_database(self):
        if not self.database_file.exists():
            raise GlassballError("Database file '{}' does not exists".format(self.database_file))
        return open_database(self.database_file)
