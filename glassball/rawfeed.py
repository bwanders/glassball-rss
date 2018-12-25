import argparse
import pprint
import textwrap

import feedparser


def indent_pprint(thing, prefix='    '):
    print(textwrap.indent(pprint.pformat(thing), prefix))


if __name__ == '__main__':
    args = argparse.ArgumentParser(description='Retrieves and dumps a raw feed')
    args.add_argument('url', help='The feed URL')
    args.add_argument('-e', '--entries', action='store_true', help='Output all entry information as well as the feed information')
    options = args.parse_args()

    feed = feedparser.parse(options.url)

    display_keys = set(feed.keys()) - {'entries'}

    first = True
    for key in sorted(display_keys):
        if not first:
            print()
        first = False
        print("{}:".format(key))
        indent_pprint(feed[key])

    if options.entries:
        print()
        print("Feed entries:")
        for entry in feed.entries:
            indent_pprint(entry)
