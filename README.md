Glassball
=========


Global Configuration
--------------------

`database` (path)

`build path` (path)

`on update` (hook), executed with location of config as working dir


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
