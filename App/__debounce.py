import time
from typing import Callable

from . import __log as _l


def debounce(delay: int) -> Callable:
    """Debounce function execution.
    Function will sleep for `delay` milliseconds before executing.
    If the function is called again before `delay` has elapsed,
    the former call will be cancelled.

    Args:
        delay (int): Delay in milliseconds.

    Returns:
        Callable: Decorator function.
    """

    def decorator(function: Callable) -> Callable:
        calls = 0

        def debounced(*args, **kwargs):
            nonlocal calls
            calls += 1
            _calls = calls
            if _calls % 1000 == 0:
                calls = 0
            time.sleep(delay / 1000)
            if _calls == calls:
                _l.debug(f"Calling {function.__name__}, {_calls}")
                return function(*args, **kwargs)
            else:
                _l.debug(f"Debounced {function.__name__} call, {_calls}")

        return debounced

    return decorator
