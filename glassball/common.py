import configparser
import os.path
import pathlib
import pkg_resources
import sqlite3


class GlassballError(Exception):
    pass


_res_manager = pkg_resources.ResourceManager()
_res_provider = pkg_resources.get_provider(__name__)

def get_resource_string(path):
    return pkg_resources.get_resource_string(__name__, path).decode('utf-8')


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

        self.build_directory = self.configuration_file.with_name(self._config['global']['build'])

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
