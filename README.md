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

`on update` (hook)

`on item` (hook)


Feed Configuration
------------------

Each feed has its own feed section.

    [feed:unique-feed-key-here]
    url = http://www.example.com/rss
    title = Human Readable Title
    update interval = 1 hour


`url` (url)

`title` (string)

`update interval` (week, day, hour, minute, second; ex. `1 day 6 hours`)

`accept bozo data` (boolean)

`style file` (path)

`on update` (hook)

`on item` (hook)
