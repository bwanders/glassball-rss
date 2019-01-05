import configparser
import contextlib
import datetime
import os
import os.path
import pathlib
import pkg_resources
import re
import shlex
import sqlite3
import subprocess
import sys


# Define errors so we can catch our own problems without difficulty
class GlassballError(Exception):
    pass


class CommandError(GlassballError):
    pass


class ConfigurationError(GlassballError):
    pass


class HookError(GlassballError):
    pass


#
# Package resource utilities
#

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


#
# Database utilities
#

def open_database(db_file):
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn


def db_datetime(value):
    return datetime.datetime(*map(int, value.replace(' ', '-').replace(':','-').split('-')))


#
# Name munging utilities
#

def slugify(s):
    s = str(s).lower()
    s = re.sub('[^a-z0-9-_]+', '-', s)
    s = s.strip('-')
    return s


def find_free_name(candidate, names):
    name = candidate
    i = 1
    while name in names:
        i += 1
        name = "{}--{}".format(candidate, i)
    return name


#
# User's hooks utilities
#

@contextlib.contextmanager
def working_directory(newdir):
    old = os.getcwd()
    os.chdir(newdir)
    try:
        yield old
    finally:
        os.chdir(old)


# Helper class to help `run_hook` recognize hook variables that can be expanded
class list_hook_var:
    def __init__(self, iterable, joiner=' '):
        self.values = [str(e) for e in iterable]
        self.joiner = joiner

    def __str__(self):
        return self.joiner.join(self.values)

    def __iter__(self):
        return iter(self.values)


def run_hook(hook_name, working_dir, command_string, replacements, environment):
    # Set up inherited environment variables by adding given environment to copy
    # of current environment
    new_env = dict(os.environ)
    new_env.update(environment)

    # Build up command by splitting the command string (in a semi-platform-aware
    # manner), and then replacing any placeholder tokens while keeping the
    # non-replacement parts.
    command = []
    for p in shlex.split(command_string, posix=not sys.platform.startswith('win')):
        # First see if the part is a replacment part, or a verbatim part
        if p.startswith('{') and p.endswith('}'):
            # Setup teplacement part information
            want_expansion = False
            key = p[1:-1]
            if key.startswith('*'):
                want_expansion = True
                key = key[1:]

            # Do sanity checks on replacement key and expansions
            if not key in replacements:
                raise HookError("{} hook command contains unknown placeholder '{}'".format(hook_name, p))
            value = replacements[key]
            if want_expansion and not isinstance(value, list_hook_var):
                raise HookError("{} hook command expands non-expandable placeholder '{}'".format(hook_name, p))

            # Replace in the manner requested
            if want_expansion:
                command.extend(value)
            else:
                command.append(str(value) if value is not None else '')
        else:
            # Append the part verbatim
            command.append(p)

    try:
        # Switch the working directory so looking up the hook command works the
        # way the caller (and the user) expects
        with working_directory(working_dir):
            result = subprocess.run(command, env=new_env, check=True)
    except subprocess.CalledProcessError as e:
        # For now, we simply pass on the hook's output directly, since we do the
        # same when the hook runs successfully (this might be changed to offer
        # the ability to log directly via our log handlers)
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        raise HookError("Failed to run {} hook: hook returned non-zero exit status {}".format(hook_name, e.returncode)) from e
    except OSError as e:
        raise HookError("Failed to run {} hook: {}".format(hook_name, e)) from e


#
# Configuration parsing utilities
#

def parse_update_interval(user_input):
    # Unit definitions (need to match the arguments for `datetime.timedelta`)
    units = ['weeks', 'days', 'hours', 'minutes', 'seconds']
    # Unit plurals and normalization table
    singular_units = [u[:-1] for u in units]
    normalize_units = {k: v for k, v in zip(singular_units, units)}

    # timedelta argument accumulator
    arguments = {}

    # Split input and sanity check number of inputs
    parts = user_input.replace(',',' ').split()
    if len(parts) % 2 != 0:
        raise ValueError("Cannot parse duration '{}'".format(user_input))

    # Set up iteration through parts per two parts
    pairs = iter(parts)
    parts_per_two = zip(pairs, pairs)
    # Run through pairs of amount and unit
    for user_amount, user_unit in parts_per_two:
        # Normalize unit and check unit validity
        unit = normalize_units.get(user_unit, user_unit)
        if unit not in units:
            raise ValueError("Unkown duration unit '{}' in '{}'".format(user_unit, user_input))
        # Set unit argument to parsed amount
        try:
            arguments[unit] = int(user_amount)
        except ValueError as e:
            raise ValueError("Cannot convert amount '{}' to a number for the '{}' part of '{}'".format(user_amount, user_unit, user_input)) from e
    # Construct a timedelta corresponding to the user's requested interval
    return datetime.timedelta(**arguments)


class Feed:
    def __init__(self, key, title, url, update_interval, accept_bozo, inject_style_file):
        self.key = key
        self.title = title
        self.url = url
        self.update_interval = update_interval
        self.accept_bozo = accept_bozo
        self.inject_style_file = inject_style_file

    @property
    def config_section(self):
        return 'feed:' + self.key


class Configuration:
    def __init__(self, ini_file):
        # Set own configuration file path
        self.configuration_file = pathlib.Path(ini_file)
        if not self.configuration_file.exists():
            raise ConfigurationError("Configuration file '{}' does not exists".format(str(self.configuration_file)))

        # Set up configuration parser and read configuration file
        self._config = configparser.ConfigParser(interpolation=None)
        try:
            self._config.read([str(self.configuration_file)], encoding='utf-8')
        except configparser.Error as e:
            raise ConfigurationError(str(e)) from e

        # Private database connection
        self._database_conn = None

        # Private feed collection
        self._feeds = {}
        for section in self._config.sections():
            # Skip all sections that are not feeds
            if not section.startswith('feed:'):
                continue
            # Get feed information from configuration
            try:
                key = section[5:]
                url = self._config.get(section, 'url')
                title = self._config.get(section, 'title', fallback=key)
                update_interval = self._config.get(section, 'update interval', fallback='1 hour')
                accept_bozo = self._config.getboolean(section, 'accept bozo data', fallback=False)
                inject_style_file = self._config.get(section, 'style file', fallback=None)
            except configparser.Error as e:
                raise ConfigurationError("Misconfiguration feed in '{}': {}".format(str(self.configuration_file), e)) from e
            # Parse update interval for feed
            try:
                update_interval = parse_update_interval(update_interval)
            except ValueError as e:
                raise ConfigurationError("Cannot understand update interval '{}' for feed '{}' in '{}'".format(update_interval, section, str(self.configuration_file)))
            # Store feed information in private collection
            self._feeds[key] = Feed(key, title, url, update_interval, accept_bozo, inject_style_file)

    @classmethod
    def exists(cls, ini_file):
        return pathlib.Path(ini_file).exists()

    @property
    def feeds(self):
        return list(self._feeds.values())

    def get_feed(self, key):
        return self._feeds.get(key, None)

    def relative_path(self, path):
        return self.configuration_file.parent / path

    # On-demand configuration keys
    @property
    def build_path(self):
        try:
            return self.relative_path(self._config.get('global', 'build path'))
        except configparser.NoOptionError as e:
            raise ConfigurationError("Missing build path in '{}': {}".format(str(self.configuration_file), e))

    @property
    def database_file(self):
        try:
            return self.relative_path(self._config.get('global', 'database'))
        except configparser.NoOptionError as e:
            raise ConfigurationError("Configuration '{}' lacks database file entry: {}".format(str(self.configuration_file), e)) from e

    @property
    def on_update(self):
        return self._config.get('global', 'on update', fallback=None)

    # Actions for the configuration
    def run_hook(self, section, hook, *, replacements={}, environment={}):
        command_string = self._config.get(section, hook, fallback=None)
        if not command_string:
            return
        if section.startswith('feed:'):
            name = "'{}' {}".format(section[5:], hook)
        else:
            name = "{} {}".format(section, hook)
        run_hook(name, self.configuration_file.parent, command_string, replacements=replacements, environment=environment)

    def open_database(self):
        if not self.database_file.exists():
            raise ConfigurationError("Database file '{}' does not exists".format(str(self.database_file)))
        return open_database(self.database_file)
