import argparse
import calendar
import datetime
import traceback

import feedparser

from .common import Configuration, db_datetime, GlassballError, CommandError, HookError, list_hook_var
from .logging import log_error, log_message


class UpdateError(GlassballError):
    def __init__(self, feed, message):
        super().__init__(message)
        self.feed = feed


def register_command(commands, common_args):
    args = commands.add_parser('update', help='Run the update process for all configured feeds', parents=[common_args])
    args.add_argument('feeds', nargs='*', default=[], help='A list of feeds to consider, by default all configured feeds are attempted')
    args.add_argument('-f', '--force', action='store_true', help='Force updates regardless of update intervals for the feeds')
    args.set_defaults(command_func=command_update)


def command_update(options):
    config = Configuration(options.config)

    # Determine which feeds we will be attempting to update
    feeds = []
    # Convert any given feed keys to actual feed references
    for key in options.feeds:
        feed = config.get_feed(key)
        if not feed:
            raise CommandError("'{}' is not a configured feed".format(key))
        feeds.append(feed)
    # If we have no feeds, we will use all of them
    if not feeds:
        feeds = config.feeds

    # Update the selected feeds
    update(config, feeds, force_update=options.force)


def update(config, feeds, force_update=False):
    conn = config.open_database()

    # Aggregates for global hooks
    new_items_info = []
    updated_feeds = set()

    for feed in feeds:
        try:
            with conn:
                success, new_items = update_feed(feed, conn, force_update=force_update)
                if not success:
                    continue

                # Run per-item hook
                for item in new_items:
                    replacements = {
                        'id': item['id'],
                        'feed': feed.key,
                        'feed-title': feed.title,
                        'published': item['published'],
                        'link': item['link'],
                        'title': item['title'],
                        'author': item['author'],
                    }
                    environment = {
                        'ITEM_ID': str(item['id']),
                        'ITEM_FEED': feed.key,
                        'ITEM_FEED_TITLE': feed.title,
                        'ITEM_PUBLISHED': item['published'],
                        'ITEM_LINK': item['link'],
                        'ITEM_TITLE': item['title'],
                        'ITEM_AUTHOR': item['author'],
                        'ITEM_CONTENT': item['content'],
                    }
                    config.run_hook(feed.config_section, 'on item', replacements=replacements, environment=environment)
                    config.run_hook('global', 'on item', replacements=replacements, environment=environment)

                # Run update hook and update aggregates for global hooks
                if new_items:
                    # Run per-feed update hook
                    config.run_hook(feed.config_section, 'on update', replacements={
                        'feed': feed.key,
                        'feed-title': feed.title,
                        'ids': list_hook_var(item['id'] for item in new_items),
                        'links': list_hook_var(item['link'] for item in new_items),
                        'titles': list_hook_var(item['title'] for item in new_items),
                    }, environment={
                        'FEED': feed.key,
                        'FEED_TITLE': feed.title,
                        'ITEM_IDS': ' '.join(str(item['id']) for item in new_items)
                    })

                    # Update aggregation list new items
                    new_items_info.extend({'id': item['id'], 'link': item['link'], 'title': item['title']} for item in new_items)
                    updated_feeds.add(feed)
        except HookError as e:
            log_error(str(e), exception=e)
            continue

    # Run global on-update hook
    if updated_feeds:
        config.run_hook('global', 'on update', replacements={
            'feeds': list_hook_var(feed.key for feed in updated_feeds),
            'feed-titles': list_hook_var(feed.title for feed in updated_feeds),
            'ids': list_hook_var(item['id'] for item in new_items_info),
            'links': list_hook_var(item['link'] for item in new_items_info),
            'titles': list_hook_var(item['title'] for item in new_items_info),
        }, environment={
            'FEEDS': ' '.join(feed.key for feed in updated_feeds),
            'ITEM_IDS': ' '.join(str(item['id']) for item in new_items_info)
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
            raise UpdateError(feed, "Error while retrieving or processing feed data: {}".format(feed_data.bozo_exception)) from feed_data.bozo_exception

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
            def get_author(thing, default=None):
                if 'author_detail' in thing and 'name' in thing.author_detail:
                    return thing.author_detail.name
                elif 'author' in thing:
                    return thing.author
                else:
                    return default

            fallback_author = get_author(feed_data.feed)

            # Build up data
            data = {
                'feed': feed.key,
                'guid': entry.id,
                'published': calendar.timegm(entry.get(selected_time_key)),
                'link': entry.get('link'),
                'title': entry.get('title'),
                'author': get_author(entry, fallback_author),
                'content': entry.get('description')
            }
            c.execute("INSERT INTO item(feed, guid, published, link, title, author, content) VALUES (:feed, :guid, datetime(:published, 'unixepoch'), :link, :title, :author, :content)", data)
            if c.lastrowid:
                data['feed'] = feed
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
