import argparse
import calendar
import datetime
import traceback

import feedparser

from .common import Configuration, db_datetime, GlassballError


class UpdateError(GlassballError):
    def __init__(self, feed, message):
        super().__init__(message)
        self.feed = feed

    def __str__(self):
        return "Feed {!r}: ".format(feed.key) + super().__str__()


def update_feed(feed, conn, now=None, force_update=False):
    if not now:
        now = datetime.datetime.utcnow()

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
        print("Not updating {feed.key}: update not forced, and last update {last_update} within {feed.update_interval} of {now}".format(
            feed=feed,
            last_update=last_update,
            now=now
        ))
        return

    try:
        feed_data = feedparser.parse(feed.url)

        # Check for bozo feed data and error out if so
        if feed_data.bozo and not feed.accept_bozo:
            raise UpdateError(feed, "Feed contains bozo data: {}".format(feed.bozo_exception)) from feed.bozo_exception

        # Update feed items
        for entry in feed_data.entries:
            # Check entry for the minimum required keys
            for key in ['id', 'updated_parsed']:
                if key not in entry:
                    raise UpdateError(feed, "Entry is missing {!r} value".format(key))

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
                'published': calendar.timegm(entry.updated_parsed),
                'link': entry.get('link'),
                'title': entry.get('title'),
                'author': entry.get('author'),
                'content': entry.get('description')
            }
            c.execute("INSERT INTO item(feed, guid, published, link, title, author, content) VALUES (:feed, :guid, datetime(:published, 'unixepoch'), :link, :title, :author, :content)", data)

        # We were succesful in retrieving and updating the feed
        success = True

    except UpdateError as e:
        print(e)
        success = False

    # Write out last update time in last_update table
    c.execute("INSERT OR REPLACE INTO last_update(feed, updated, success) VALUES(:feed, datetime(:updated, 'unixepoch'), :success)", {
        'feed': feed.key,
        'updated': now.replace(tzinfo=datetime.timezone.utc).timestamp(),
        'success': success
    })


if __name__ == '__main__':
    args = argparse.ArgumentParser(description='Updates the feed item database')
    args.add_argument('name', nargs='?', default='feeds.ini', help='The configuration file')
    args.add_argument('-f', '--force', action='store_true', help='Force updates regardless of update intervals for the feeds')
    options = args.parse_args()

    config = Configuration(options.name)

    conn = config.open_database()

    for feed in config.feeds:
        with conn:
            update_feed(feed, conn, force_update=options.force)
