import argparse

from .common import Configuration


if __name__ == '__main__':
    args = argparse.ArgumentParser(description='Lists the feeds and feed items')
    args.add_argument('name', nargs='?', default='feeds.ini', help='The configuration file')
    options = args.parse_args()

    config = Configuration(options.name)

    with config.open_database() as conn:
        c = conn.cursor()
        for feed in config.feeds:
            print("{} <{}>".format(feed.title, feed.url))
            c.execute("SELECT title, author, published, link FROM item WHERE feed = ? ORDER BY published DESC", (feed.key,))
            feed_items = c.fetchall()
            for item in feed_items:
                print("  {title} <{link}>\n    by {author}, at {published}".format(**item))
