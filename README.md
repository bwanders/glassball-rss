Glassball
=========

Glassball RSS is an RSS/Atom feed tracker built to be used as a cronjob, instead of running as a daemon. Glassball offers a simple configuration format, can run updates when you want them (and invoke script hooks on specific events), and can produce a simple static HTML viewer for the feeds you are tracking.

Glassball RSS requires python 3.5 (or higher). Feed parsing is handled by the very pragmatic [feedparser](https://pypi.org/project/feedparser/) package.


Quick Start
-----------

Set up a virtual environment of your preferred flavour, and get the glassball package set up by checking out repo and installing requirements.

Initialize a glassball configuration:

    python3 -m glassball init

Add feeds by URL or import an OPML file (add `-w` argument to write directly to the configuration file):

    python3 -m glassball add https://some.feed.url/here

    python3 -m glassball import file.opml

With a few feeds configured run updates and build static viewer:

    python3 -m glassball update

    python3 -m glassball build

The update command is intended to be run from a cronjob, and automatically handles update intervals for feeds to prevent hitting each feed every time.


Configuration
=============

Glassball configuration is based on Python's [configparser](https://docs.python.org/3/library/configparser.html) module. A configuration file consists of sections with keys:

    [global]
    database = feeds.db
    build path = build

    [feed:schlock]
    url = https://www.schlockmercenary.com/rss/
    title = Schlock Mercenary

This example configuration file contains a `[global]` section, a feed section `[feed:schlock]` sections. Each added feed section describes an RSS/Atom feed to
track.

All paths in the configuration are relative to the location of the configuration file itself.

Technical note: glassball expects the configuration file to be in UTF-8 encoding, and string interpolation is disabled.


Global Configuration
--------------------

`database` (path): The location of the database file to be used with this configuration. Has no default value.

`build path` (path): The output path where the produced static viewer is placed.  Has no default value.

`on update` (hook): See the Global `on update` hook section. Defaults to not having a global on update hook.

`on item` (hook): See the `on item` hooks section. Defaults to not having a global on item hook.


Feed Configuration
------------------

Each feed has its own feed section.

    [feed:unique-feed-key-here]
    url = http://www.example.com/rss
    title = Human Readable Title
    update interval = 1 hour

`url` (url): The mandatory URL for this feed. Has no default value.

`title` (string): A human-readable title for this feed. Defaults to using the feed's key as defined in the section header.

`update interval` (interval): The update interval for the feed, the feed is checked no more than once per interval. Intervals are given as `1 hour, 30  minutes`, usable units are week, day, hour, minute, and second. Defaults to 1 hour.

`accept bozo data` (boolean): Whether the feed update should attempt to process the feed even if it contains errors or just plain bozo data. Given as `yes` or `no`. Defaults to no.

`style file` (path): The path to a CSS file that is included in the static viewer's per-item HTML file to allow styling specific for this feed's item. This is useful for some types of automatically generated feeds, to make them a little more palatable out of their original context. Defaults to not including a style file.

`on update` (hook): See the per-feed `on update` hook section. Defaults to not having an on update hook for this specific feed.

`on item` (hook): See the `on item` hooks section. Defaults to not having an on item hook for this specific feed.



Hooks
=====

All hooks are executed with the configuration location as the working directory. Environment variables are available depending on the event for which the hook is invoked.

Addtionally, hook command can contain placeholders arguments of the form `{name}`. Note that the placeholders are not replaced inside strings or other parameters, they are only replaced if they are a distinct parameter. For example:

    [global]
    on update = update-hook.sh "some parameter" {feeds}

Will invoke the `update-hook.sh` script with 2 parameters, the first being the verbatim `some parameter` and the second a space-separated list of feed keys.

Placeholders without a value (such as the `author` placeholder for a new item that has no author) will produce an empty parameter.

Some placeholders represent lists. They can be used directly (in which case the items in the list will be separated by a space. These placeholders can also be expanded into separate parameters. To expand a placeholder use the form `{*name}`, this will expand the placeholder to a parameter per list item.


Global `on update` Hook
-----------------------

Invoked if one or more feeds updated with new items. This hook is invoked after all other hooks have had a chance to run.

Replacements:

  - `feeds` A list of feed keys.
  - `feed-titles` A list of feed titles, in the same order as the keys.
  - `ids` A list of item ids.
  - `links` A list of item links, in the same order as the ids.
  - `titles` A list of item titles, in the same order as the ids.

Environment:

  - `FEEDS` A space-separated list of feed keys.
  - `ITEM_IDS` A space-separated list of item ids.


Per Feed `on update` Hook
-------------------------

Invoked if the current feed is updated with new items. This hook is invoked at the end of updating the current feed. A non-zero exit code from this hook rolls back the feed's update: no new items will be added, and the feed will not count for the global on update hook.

Replacements:

  - `feed` The feed key for the current feed.
  - `feed-title` The current feed's title.
  - `ids` A list of item ids.
  - `links` A list of item links, in the same order as the ids.
  - `titles` A list of item titles, in the same order as the ids.

Environment:

  - `FEED` The feed key for the current feed.
  - `FEED_TITLE` The current feed's title.
  - `ITEM_IDS` A space-separated list of new item ids.



The `on item` Hooks
-------------------

Both the global and per-feed version of the on item hook operate in the same way. This hook is invoked for each new item, the per-feed hook runs first, followed by the global hook. A non-zero exit code from either version of this hook rolls back the feed's update: no new items will be added, and the feed will not count for the global on update hook.

Replacements:

  - `id`: The new item id.
  - `feed`: The feed key of the current feed.
  - `feed-title`: The current feed's title.
  - `published`: The date of publication for this item, formatted in iso8601 ordered `YYYY-MM-DD HH:MM:SS` format.
  - `link`: The link for the new item.
  - `title`: The title of the new item.
  - `author`: The author of the new item.

Environment:
  - `ITEM_ID` The new item id.
  - `ITEM_FEED` The feed key of the current feed.
  - `ITEM_FEED_TITLE` The current feed's title.
  - `ITEM_PUBLISHED`  The date of publication for this item, formatted in iso8601 ordered `YYYY-MM-DD HH:MM:SS` format.
  - `ITEM_LINK` The link for the new item.
  - `ITEM_TITLE` The title of the new item.
  - `ITEM_AUTHOR` The author of the new item.
  - `ITEM_CONTENT` The normalize content of the new item.


License
=======

MIT License, see LICENSE.

Copyright (c) 2018-2018 Brend Wanders
