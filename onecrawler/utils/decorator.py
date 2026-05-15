import inspect
import time
from typing import Any, Callable, Tuple


async def calculate_execution_time(
    func: Callable[..., Any], *args: Any, **kwargs: Any
) -> Tuple[float, Any]:
    """Measures the execution time of a synchronous or asynchronous function.

    Args:
        func (Callable[..., Any]): The function or coroutine to measure.
        *args (Any): Positional arguments to pass to the function.
        **kwargs (Any): Keyword arguments to pass to the function.

    Returns:
        Tuple[float, Any]: A tuple containing the elapsed time in seconds (float)
            and the result of the function call (Any).
    """
    start = time.perf_counter()
    result = func(*args, **kwargs)
    if inspect.isawaitable(result):
        result = await result
    elapsed = time.perf_counter() - start
    return elapsed, result
