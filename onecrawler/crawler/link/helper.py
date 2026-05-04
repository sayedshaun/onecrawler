import asyncio
import logging
import random
from fnmatch import fnmatch
from urllib.parse import urlparse


async def human_delay(min_s: float = 0.3, max_s: float = 1.2) -> None:
    await asyncio.sleep(random.uniform(min_s, max_s))


async def human_scroll(page: any, max_scrolls: int = 20) -> None:
    try:
        for _ in range(max_scrolls):
            await page.mouse.wheel(0, random.randint(400, 800))
            await asyncio.sleep(random.uniform(0.2, 0.6))
    except Exception as e:
        logging.warning(f"Error during human-like scrolling: {e}")


async def human_mouse_move(page: any) -> None:
    try:
        for _ in range(random.randint(5, 15)):
            x = random.randint(0, 1366)
            y = random.randint(0, 768)
            await page.mouse.move(x, y, steps=random.randint(5, 20))
            await asyncio.sleep(random.uniform(0.1, 0.3))
    except Exception as e:
        logging.warning(f"Error during human-like mouse movement: {e}")


def wildcard_link_match(
    link: str, base_prefix: str, include_pattern: list[str]
) -> bool:
    if not isinstance(link, str) or not link.startswith(base_prefix):
        return False

    if include_pattern:
        path = urlparse(link).path
        return any(fnmatch(path, pattern) for pattern in include_pattern)
    return True
