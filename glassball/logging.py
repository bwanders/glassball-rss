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

log_handlers = []


@contextlib.contextmanager
def file_log_handler(file):
    with open(file, 'a', encoding='utf-8') as f:
        def log_to_file(entry):
            print(entry, file=f)
        push_log_handler(log_to_file)
        try:
            yield None
        finally:
            pop_log_handler()


def push_log_handler(handler):
    log_handlers.append(handler)


def pop_log_handler():
    log_handlers.pop()


def log_entry(kind, message, when):
    entry = LogEntry(kind, message, when)
    for handler in log_handlers:
        handler(entry)


def log_message(message):
    log_entry('message', message, datetime.datetime.now())


def log_error(message, exception=None):
    log_entry('error', message, datetime.datetime.now())
