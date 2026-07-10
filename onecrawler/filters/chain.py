from .base import FilterChain


def AND(*filters):
    """Combine filters so an item passes only if ALL of them accept it.

    Args:
        *filters (Callable[[dict], bool]): Filter predicates to combine.

    Returns:
        FilterChain: A predicate accepting an item only when every filter does.
    """
    return FilterChain(*filters, mode="AND")


def OR(*filters):
    """Combine filters so an item passes if ANY of them accepts it.

    Args:
        *filters (Callable[[dict], bool]): Filter predicates to combine.

    Returns:
        FilterChain: A predicate accepting an item when at least one filter does.
    """
    return FilterChain(*filters, mode="OR")


def NOT(f):
    """Negate a filter predicate.

    Args:
        f (Callable[[dict], bool]): The filter predicate to negate.

    Returns:
        Callable[[dict], bool]: A predicate accepting an item only when ``f``
        rejects it.
    """

    def _neg(item):
        return not f(item)

    return _neg
