"""Optional execution tracing for service functions."""

import functools
import logging
import time

logger = logging.getLogger('futnetnepal.trace')


def log_execution(*, level=logging.DEBUG):
    """Log function entry, exit, duration, and exceptions (for critical paths)."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = f'{func.__module__}.{func.__qualname__}'
            started = time.perf_counter()
            logger.log(level, 'CALL %s', name)
            try:
                result = func(*args, **kwargs)
            except Exception:
                elapsed_ms = (time.perf_counter() - started) * 1000
                logger.exception('FAIL %s | %.1fms', name, elapsed_ms)
                raise
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.log(level, 'DONE %s | %.1fms', name, elapsed_ms)
            return result

        return wrapper

    return decorator
