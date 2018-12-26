import contextlib
import datetime
import pathlib


class LogEntry:
    def __init__(self, kind, message, when):
        self.kind = kind
        self.message = message
        self.when = when

    def __str__(self):
        return "[{}] {}: {}".format(self.when, self.kind, self.message)

log_handlers = [print]


def log_entry(kind, message, when):
    entry = LogEntry(kind, message, when)
    for handler in log_handlers:
        handler(entry)


def log_message(message):
    log_entry('message', message, datetime.datetime.now())


def log_error(message, exception=None):
    log_entry('error', message, datetime.datetime.now())
