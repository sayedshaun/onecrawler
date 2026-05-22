from .base import FilterChain


def AND(*filters):
    return FilterChain(*filters, mode="AND")


def OR(*filters):
    return FilterChain(*filters, mode="OR")


def NOT(f):
    def _neg(item):
        return not f(item)

    return _neg
