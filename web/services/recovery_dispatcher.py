"""Bounded process-local admission; no durable queue or delivery promise."""
from concurrent.futures import ThreadPoolExecutor
from contextvars import Context
import logging
from threading import BoundedSemaphore, Lock

logger=logging.getLogger(__name__)


class RecoveryDispatcher:
    def __init__(self,*,workers=2,capacity=32):
        if workers<1 or capacity<workers:
            raise ValueError('Invalid recovery capacity')
        self._executor=ThreadPoolExecutor(max_workers=workers,thread_name_prefix='account-recovery')
        self._slots=BoundedSemaphore(capacity)
        self._lock=Lock()
        self._closed=False
        self._pending=0

    def submit(self,operation,*args):
        with self._lock:
            if self._closed or not self._slots.acquire(blocking=False):
                return False
            self._pending+=1
            try:
                future=self._executor.submit(Context().run,operation,*args)
            except Exception:
                self._pending-=1
                self._slots.release()
                return False
        def finished(result):
            try:
                if not result.cancelled():
                    result.result()
            except Exception as error:
                logger.error('Recovery job failed class=%s',type(error).__name__)
            finally:
                with self._lock:
                    self._pending-=1
                    self._slots.release()
        future.add_done_callback(finished)
        return True

    @property
    def pending(self):
        with self._lock:
            return self._pending

    def close(self):
        with self._lock:
            self._closed=True
        # Cancels only jobs not started. SDK's bounded timeout owns running jobs.
        self._executor.shutdown(wait=False,cancel_futures=True)
