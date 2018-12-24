import argparse
import calendar
import feedparser

from .common import Configuration


def update_feed(feed, conn):
    c = conn.cursor()
    feed_data = feedparser.parse(feed.url)
    for entry in feed_data.entries:
        c.execute('SELECT EXISTS (SELECT * FROM item WHERE guid = :guid)', {
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


if __name__ == '__main__':
    args = argparse.ArgumentParser(description='Updates the feed item database')
    args.add_argument('name', nargs='?', default='feeds.ini', help='The configuration file')
    options = args.parse_args()

    config = Configuration(options.name)

    with config.open_database() as conn:
        for feed in config.feeds:
            update_feed(feed, conn)
