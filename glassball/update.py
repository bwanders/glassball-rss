import argparse
import calendar
import datetime

import feedparser

from .common import Configuration, db_datetime


def update_feed(feed, conn, now=None, force_update=False):
    if not now:
        now = datetime.datetime.utcnow()

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

        # Update feed items
        for entry in feed_data.entries:
            c.execute("SELECT EXISTS (SELECT * FROM item WHERE guid = :guid)", {
                'guid': entry.id
            })

            result = c.fetchall()
            entry_exists = result and result[0][0]
            if entry_exists:
                continue

            data = {
                'feed': feed.key,
                'guid': entry.id,
                'published': calendar.timegm(entry.updated_parsed),
                'link': entry.link,
                'title': entry.title,
                'author': entry.author,
                'content': entry.description
            }
            c.execute("INSERT INTO item(feed, guid, published, link, title, author, content) VALUES (:feed, :guid, datetime(:published, 'unixepoch'), :link, :title, :author, :content)", data)

        # Write out last update time in last_update table
        c.execute("INSERT OR REPLACE INTO last_update(feed, updated) VALUES(:feed, datetime(:updated, 'unixepoch'))", {
            'feed': feed.key,
            'updated': now.replace(tzinfo=datetime.timezone.utc).timestamp()
        })
    except Exception as e:
        raise e


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
