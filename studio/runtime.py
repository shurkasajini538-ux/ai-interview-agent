"""Operation-scoped progress, usage and cooperative cancellation."""
import contextvars
import threading
import time
from contextlib import contextmanager

CURRENT = contextvars.ContextVar('studio_operation', default=None)


class Cancelled(Exception):
    pass


class Operation:
    def __init__(self):
        self.events = []
        self.usage = []
        self.cancelled = threading.Event()
        self.lock = threading.RLock()
        self.committed = False
        self.started = time.monotonic()

    def check(self):
        if self.cancelled.is_set() and not self.committed:
            raise Cancelled('操作已取消，未保存新的练习结果。')

    def emit(self, kind, **data):
        self.check()
        with self.lock:
            self.events.append({'sequence':len(self.events)+1, 'kind':kind,
                                'elapsed_ms':round((time.monotonic()-self.started)*1000), **data})

    def commit(self, callback):
        with self.lock:
            self.check()
            result = callback()
            self.committed = True
            return result


@contextmanager
def operation_context(operation):
    token = CURRENT.set(operation)
    try:
        yield operation
    finally:
        CURRENT.reset(token)


def checkpoint():
    current = CURRENT.get()
    if current:
        current.check()


def emit(kind, **data):
    current = CURRENT.get()
    if current:
        current.emit(kind, **data)


def commit(callback):
    current = CURRENT.get()
    return current.commit(callback) if current else callback()


def usage(record):
    current = CURRENT.get()
    if current:
        with current.lock:
            current.usage.append(record)


def metrics():
    current = CURRENT.get()
    if not current:
        return {'requests':0, 'prompt_tokens':0, 'completion_tokens':0, 'elapsed_ms':0, 'usage_available':False}
    return {'requests':len(current.usage),
            'prompt_tokens':sum(x.get('prompt_tokens') or 0 for x in current.usage),
            'completion_tokens':sum(x.get('completion_tokens') or 0 for x in current.usage),
            'usage_available':any(x.get('usage_available') for x in current.usage),
            'elapsed_ms':round((time.monotonic()-current.started)*1000)}
