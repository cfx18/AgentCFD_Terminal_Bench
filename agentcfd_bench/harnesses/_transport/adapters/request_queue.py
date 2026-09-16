"""FIFO admission for one active provider request, independent of HTTP workers."""
from collections import deque
from contextlib import contextmanager
import threading
import time


class QueueCancelled(Exception):
    pass


class SerialRequests:
    def __init__(self):
        self.condition = threading.Condition()
        self.waiting = deque()
        self.active = None

    @contextmanager
    def admit(self, waiting, *, interval=1):
        token, began, acquired = object(), time.monotonic(), False
        with self.condition:
            self.waiting.append(token)
        try:
            while True:
                with self.condition:
                    if self.active is None and self.waiting[0] is token:
                        self.active = self.waiting.popleft()
                        acquired = True
                        break
                # Heartbeats/cancellation are OUTSIDE the lock: slow clients do
                # not hold admission or block an active request's completion.
                if not waiting(time.monotonic()-began):
                    raise QueueCancelled()
                with self.condition:
                    self.condition.wait(timeout=interval)
            yield time.monotonic()-began
        finally:
            with self.condition:
                if acquired:
                    self.active = None
                elif token in self.waiting:
                    self.waiting.remove(token)
                self.condition.notify_all()
