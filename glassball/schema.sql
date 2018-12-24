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
