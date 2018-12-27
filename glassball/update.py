import argparse
import calendar
import datetime
import traceback

import feedparser

from .common import Configuration, db_datetime, GlassballError
from .logging import log_error, log_message


import contextlib
import os
import shlex
import subprocess
import sys


class UpdateError(GlassballError):
    def __init__(self, feed, message):
        super().__init__(message)
        self.feed = feed

    def __str__(self):
        return "Feed '{}': ".format(self.feed.key) + super().__str__()


def register_command(commands, common_args):
    args = commands.add_parser('update', help='Run the update process for all configured feeds', parents=[common_args])
    args.add_argument('-f', '--force', action='store_true', help='Force updates regardless of update intervals for the feeds')
    args.set_defaults(command_func=command_update)


def command_update(options):
    config = Configuration(options.config)
    update(config, force_update=options.force)


def run_hook(config, hook_name, command_string, replacements, environment):
    @contextlib.contextmanager
    def working_directory(newdir):
        old = os.getcwd()
        os.chdir(newdir)
        try:
            yield old
        finally:
            os.chdir(old)

    # Set up inherited environment variables by adding given environment to copy
    # of current environment
    new_env = dict(os.environ)
    new_env.update(environment)

    # Set up placeholders by taking replacements and wrapping all keys in `{}`
    placeholders = {('{' + k + '}'): v for k, v in replacements.items()}
    command = []

    # Build up command by splitting the command string (in a semi-platform-aware
    # manner), and then replacing any placeholder tokens while keeping the
    # non-replacement parts.
    for p in shlex.split(command_string, posix=not sys.platform.startswith('win')):
        if p.startswith('{') and p.endswith('}'):
            try:
                command.append(str(replacements[p[1:-1]]))
            except KeyError as e:
                raise GlassballError("{} hook command '{}' contains unknown placeholder '{}'".format(hook_name, command_string, p))
        else:
            # Part is used verbatim
            command.append(p)

    try:
        # Switch the working directory so looking up the hook command will be
        # done relative to the configuration file
        with working_directory(config.configuration_file.parent):
            result = subprocess.run(command, env=new_env)
    except OSError as e:
        raise GlassballError("Failed to run {} hook '{}': {}".format(hook_name, command[0], e)) from e


def update(config, force_update=False):
    conn = config.open_database()

    new_item_count = 0
    for feed in config.feeds:
        with conn:
            success, new_items = update_feed(feed, conn, force_update=force_update)
            if success:
                new_item_count += len(new_items)

    if config.on_update and new_item_count > 0:
        run_hook(config, "Global on update", config.on_update, replacements={'count': new_item_count}, environment={})


def update_feed(feed, conn, now=None, force_update=False):
    if not now:
        now = datetime.datetime.utcnow()

    new_items = []
    success = False
    c = conn.cursor()

    # Retrieve the last update time from the database
    c.execute("SELECT updated FROM last_update WHERE feed = :feed", {
        'feed': feed.key
    })
    row = c.fetchone()
    last_update = db_datetime(row['updated']) if row else None

    needs_update = force_update or last_update is None or last_update + feed.update_interval < now
    if not needs_update:
        return True, []

    try:
        feed_data = feedparser.parse(feed.url)

        # Check for bozo feed data and error out if so
        if feed_data.bozo and not feed.accept_bozo:
            raise UpdateError(feed, "Feed contains bozo data: {}".format(feed.bozo_exception)) from feed.bozo_exception

        # Update feed items
        for entry in feed_data.entries:
            # Make sure we have an actual entry identifier. If we have no such
            # identifier we can not handle the entry.
            if 'id' not in entry:
                raise UpdateError(feed, "Entry is missing identifier")

            # First, check if we have the `published` or `updated` key,
            # prefering to use `published`
            selected_time_key = None
            for selected_time_key in ['published_parsed', 'updated_parsed']:
                if selected_time_key in entry:
                    break
            else:
                raise UpdateError(feed, "Entry is missing both 'published' and 'updated' times")

            # Check the entry for existince in database
            c.execute("SELECT EXISTS (SELECT * FROM item WHERE guid = ?)", (entry.id,))
            result = c.fetchall()
            entry_exists = result and result[0][0]
            if entry_exists:
                continue

            # Build up the local data about the feed entry. This includes
            # mandatory data such as the feed it belongs to, the entry id, and
            # the moment of publication. Any other fields are optional.
            data = {
                'feed': feed.key,
                'guid': entry.id,
                'published': calendar.timegm(entry.get(selected_time_key)),
                'link': entry.get('link'),
                'title': entry.get('title'),
                'author': entry.get('author'),
                'content': entry.get('description')
            }
            c.execute("INSERT INTO item(feed, guid, published, link, title, author, content) VALUES (:feed, :guid, datetime(:published, 'unixepoch'), :link, :title, :author, :content)", data)
            if c.lastrowid:
                data['id'] = c.lastrowid
                data['published'] = str(datetime.datetime.fromtimestamp(data['published']))
                new_items.append(data)

        # We were succesful in retrieving and updating the feed
        success = True

    except UpdateError as e:
        log_error("Feed '{}': {}".format(e.feed.key, e), exception=e)
        success = False
        new_items = []

    # Write out last update time in last_update table
    c.execute("INSERT OR REPLACE INTO last_update(feed, updated, success) VALUES(:feed, datetime(:updated, 'unixepoch'), :success)", {
        'feed': feed.key,
        'updated': now.replace(tzinfo=datetime.timezone.utc).timestamp(),
        'success': success
    })

    return success, new_items
