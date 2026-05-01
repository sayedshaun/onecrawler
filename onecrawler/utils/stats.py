import inspect
import time
from typing import Any, Callable, Tuple


async def time_function(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Tuple[float, Any]:
    """Measure execution time for sync or async functions.

    Args:
        func: A regular or coroutine function.
        *args: Positional arguments for func.
        **kwargs: Keyword arguments for func.

    Returns:
        A tuple of (elapsed_seconds, result).
    """
    start = time.perf_counter()
    result = func(*args, **kwargs)
    if inspect.isawaitable(result):
        result = await result
    elapsed = time.perf_counter() - start
    return elapsed, result
