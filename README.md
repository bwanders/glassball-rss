Glassball
=========

Hooks
-----

All hooks are executed with the configuration location is working directory.

Hook command can contain placeholders arguments of the form `{name}`. Note that the placeholders are not replaced inside strings or other parameters, they are only replaced if they are a distinct parameter.

Some placeholders represent lists. They can be used directly (in which case the items in the list will be separated by a space. These placeholders can also be expanded into separate parameters. To expand a placeholder use the form `{*name}`, this will expand the placeholder to a parameter per list item.


Global Configuration
--------------------

`database` (path)

`build path` (path)

`on update` (hook) See the Global `on update` hook section

`on item` (hook) See the `on item` hooks section


Feed Configuration
------------------

Each feed has its own feed section.

    [feed:unique-feed-key-here]
    url = http://www.example.com/rss
    title = Human Readable Title
    update interval = 1 hour


`url` (url) *mandatory*

`title` (string)

`update interval` (week, day, hour, minute, second; ex. `1 day 6 hours`)

`accept bozo data` (boolean)

`style file` (path)

`on update` (hook) See the per-feed `on update` hook section

`on item` (hook) See the `on item` hooks section


Global `on update` Hook
-----------------------

Replacements:

  - `feeds`
  - `feed-titles`
  - `ids`
  - `links`
  - `titles`

Environment:

  - `FEEDS`
  - `ITEM_IDS`


Per Feed `on update` Hook
-------------------------

Replacements:

  - `feed`
  - `feed-title`
  - `ids`
  - `links`
  - `titles`

Environment:

  - `FEED`
  - `FEED_TITLE`
  - `ITEM_IDS`



The `on item` Hooks
-------------------

Replacements:

  - `id`:
  - `feed`:
  - `feed-title`:
  - `published`:
  - `link`:
  - `title`:
  - `author`:

Environment:
  - `ITEM_ID`
  - `ITEM_FEED`
  - `ITEM_FEED_TITLE`
  - `ITEM_PUBLISHED`
  - `ITEM_LINK`
  - `ITEM_TITLE`
  - `ITEM_AUTHOR`
  - `ITEM_CONTENT`
