-- Database ID is used to reset "client side" read/unread status for items
CREATE TABLE database_id (id TEXT NOT NULL);


-- Last update times per feed
CREATE TABLE last_update (
    feed TEXT NOT NULL PRIMARY KEY,
    updated TEXT NOT NULL,
    success BOOLEAN NOT NULL
);


-- Feed items
CREATE TABLE item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed TEXT NOT NULL,

    guid TEXT NOT NULL,
    published TEXT NOT NULL,
    link TEXT,
    title TEXT,
    author TEXT,
    content TEXT
);
