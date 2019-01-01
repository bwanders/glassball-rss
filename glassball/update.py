import argparse
import calendar
import datetime
import traceback

import feedparser

from .common import Configuration, db_datetime, GlassballError, list_hook_var
from .logging import log_error, log_message


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


def update(config, force_update=False):
    conn = config.open_database()

    new_item_count = 0
    for feed in config.feeds:
        with conn:
            success, new_items = update_feed(feed, conn, force_update=force_update)
            if success:
                new_item_count += len(new_items)
                if new_items:
                    config.run_hook(feed.section, 'on update', replacements={
                        'feed': feed.key,
                        'count': len(new_items),
                        'ids': list_hook_var(item['id'] for item in new_items)
                    })

    if new_item_count > 0:
        config.run_hook('global', 'on update', replacements={
            'count': new_item_count
        })


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

            # Determine fallback author
            fallback_author = None
            if 'author_detail' in feed_data.feed and 'name' in feed_data.feed.author_detail:
                fallback_author = feed_data.feed.author_detail.name
            elif 'author' in feed_data.feed:
                fallback_author = feed_data.feed.author

            # Build up data
            data = {
                'feed': feed.key,
                'guid': entry.id,
                'published': calendar.timegm(entry.get(selected_time_key)),
                'link': entry.get('link'),
                'title': entry.get('title'),
                'author': entry.get('author', fallback_author),
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
