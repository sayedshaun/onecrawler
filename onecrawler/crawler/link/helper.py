import asyncio
import logging
import random
from fnmatch import fnmatchcase
from typing import List
from urllib.parse import urlparse

from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def human_delay(min_s: float = 0.3, max_s: float = 1.2) -> None:
    """Simulates a human-like delay between actions.

    Args:
        min_s (float): Minimum delay in seconds.
        max_s (float): Maximum delay in seconds.
    """
    await asyncio.sleep(random.uniform(min_s, max_s))


async def human_scroll(page: Page, max_scrolls: int = 10) -> None:
    """Simulates human-like scrolling behavior on a page.

    Scrolls to the bottom of the page repeatedly until either the maximum
    number of scrolls is reached or the page height stops increasing.

    Args:
        page (Page): The Playwright Page instance.
        max_scrolls (int): The maximum number of scroll actions to perform.
    """
    try:
        last_height = await page.evaluate("document.body.scrollHeight")

        for _ in range(max_scrolls):

            await page.evaluate("""
                window.scrollTo(
                    0,
                    document.body.scrollHeight
                )
            """)

            await asyncio.sleep(1)

            new_height = await page.evaluate("document.body.scrollHeight")

            if new_height == last_height:
                break

            last_height = new_height

    except Exception as e:
        logger.warning(f"Scroll error: {e}")


async def human_mouse_move(
    page: Page,
    *,
    min_mouse_moves: int,
    max_mouse_moves: int,
    mouse_width: int,
    mouse_height: int,
    min_mouse_steps: int,
    max_mouse_steps: int,
    min_mouse_sleep: float,
    max_mouse_sleep: float,
) -> None:
    try:
        for _ in range(
            random.randint(
                min_mouse_moves,
                max_mouse_moves,
            )
        ):
            x = random.randint(0, mouse_width)
            y = random.randint(0, mouse_height)

            await page.mouse.move(
                x,
                y,
                steps=random.randint(
                    min_mouse_steps,
                    max_mouse_steps,
                ),
            )

            await asyncio.sleep(
                random.uniform(
                    min_mouse_sleep,
                    max_mouse_sleep,
                )
            )

    except Exception as e:
        logging.warning(f"Error during human-like mouse movement: {e}")


def wildcard_link_match(
    link: str, base_prefix: str, include_pattern: List[str]
) -> bool:
    """Return True if *link* belongs to the site and matches the section filter.

    Args:
        link:             The candidate URL.
        base_prefix:      Site origin, e.g. ``"https://www.example.com"``.
        include_patterns: Glob patterns tested against the URL *path*.
                          An empty list means "accept everything".

    Examples::

        wildcard_link_match(
            "https://www.example.com/sports/football/123",
            "https://www.example.com",
            ["/sports/*"],
        )  # True

        wildcard_link_match(
            "https://www.example.com/tech/ai/456",
            "https://www.example.com",
            ["/sports/*"],
        )  # False

        wildcard_link_match(
            "https://www.example.com/anything",
            "https://www.example.com",
            [],            # no filter → always True
        )  # True
    """

    if not isinstance(link, str) or not link.startswith(base_prefix):
        return False

    if include_pattern:
        path = urlparse(link).path
        return any(fnmatchcase(path, pattern) for pattern in include_pattern)
    return True
