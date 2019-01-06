import argparse

from .common import Configuration, db_datetime, log_error, log_message


def register_command(commands, common_args):
    args = commands.add_parser('list', help='Lists feed information and feed items', parents=[common_args])
    args.add_argument('-a', '--articles', action='store_true', help='Lists articles as well')
    args.set_defaults(command_func=command_list)


def command_list(options):
    config = Configuration(options.config)

    with config.open_database() as conn:
        c = conn.cursor()
        for feed in config.feeds:
            c.execute("SELECT updated FROM last_update WHERE feed = ?", (feed.key,))
            row = c.fetchone()
            last_update = db_datetime(row['updated']) if row else None

            print("[{}] {} <{}>  (last update {})".format(feed.key, feed.title, feed.url, last_update or 'unknown'))

            if options.articles:
                c.execute("SELECT title, author, published, link FROM item WHERE feed = ? ORDER BY published DESC", (feed.key,))
                feed_items = c.fetchall()
                for item in feed_items:
                    print("  {title} <{link}>\n    by {author}, at {published}".format(**item))
