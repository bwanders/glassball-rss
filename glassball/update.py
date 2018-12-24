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
            feed_url = config.get(section, 'url')

            feed_data = feedparser.parse(feed_url)
            for entry in feed_data.entries:
                c.execute('SELECT EXISTS (SELECT * FROM item WHERE guid = :guid)', {
                    'guid': entry.id
                })

                result = c.fetchall()
                entry_exists = result and result[0][0]
                if entry_exists:
                    continue

                data = {
                    'feed': feed,
                    'guid': entry.id,
                    'published': calendar.timegm(entry.updated_parsed),
                    'link': entry.link,
                    'title': entry.title,
                    'author': entry.author,
                    'content': entry.description
                }
                c.execute("INSERT INTO item(feed, guid, published, link, title, author, content) VALUES (:feed, :guid, datetime(:published, 'unixepoch'), :link, :title, :author, :content)", data)
