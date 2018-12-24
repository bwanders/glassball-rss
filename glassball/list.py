import argparse
import calendar
import configparser
import pathlib
import sqlite3

import feedparser


if __name__ == '__main__':
    args = argparse.ArgumentParser(description='Initialize a glassball configuration')
    args.add_argument('name', nargs='?', default='feeds.ini', help='The name of the configuration and database files')
    options = args.parse_args()

    ini_file = pathlib.Path(options.name)
    config = configparser.ConfigParser()
    config.read(ini_file, encoding='utf-8')

    db_file = ini_file.with_name(config['global']['database'])

    if not db_file.exists():
        args.error("Database file '{}' does not exists".format(db_file))

    with sqlite3.connect(db_file) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        for section in config.sections():
            if not section.startswith('feed:'):
                continue

            feed = section[5:]
            feed_title = config.get(section, 'title', fallback=feed)
            feed_url = config.get(section, 'url')
            print("{} <{}>".format(feed_title, feed_url))
            c.execute("SELECT title, author, published, link FROM item WHERE feed = ? ORDER BY published DESC", (feed,))
            feed_items = c.fetchall()
            for item in feed_items:
                print("  {title} <{link}>\n    by {author}, at {published}".format(**item))
