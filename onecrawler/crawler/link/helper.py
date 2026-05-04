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


async def scroll_to_bottom_with_infinite_scroll(
    page: any,
    max_scroll_attempts: int = 50,
    scroll_pause_time: float = 1.0,
    check_new_content_time: float = 2.0,
) -> None:
    """
    Scroll to bottom of page with support for infinite scroll loading.
    Waits for network to settle after each scroll to load new content.
    """
    try:
        previous_height = await page.evaluate("() => document.body.scrollHeight")
        scroll_attempts = 0
        no_change_count = 0

        while scroll_attempts < max_scroll_attempts and no_change_count < 3:
            await page.evaluate("() => window.scrollBy(0, window.innerHeight)")

            await asyncio.sleep(
                random.uniform(scroll_pause_time * 0.7, scroll_pause_time * 1.3)
            )

            try:
                await page.wait_for_load_state(
                    "domcontentloaded", timeout=check_new_content_time * 1000
                )
            except Exception:
                await asyncio.sleep(check_new_content_time)

            new_height = await page.evaluate("() => document.body.scrollHeight")

            if new_height == previous_height:
                no_change_count += 1
                logging.debug(f"No new content loaded (attempt {no_change_count}/3)")
            else:
                no_change_count = 0
                logging.debug(
                    f"New content detected. Height: {previous_height} -> {new_height}"
                )
                previous_height = new_height

            scroll_attempts += 1

        logging.debug(f"Infinite scroll completed after {scroll_attempts} attempts")
    except Exception as e:
        logging.warning(f"Error during infinite scroll: {e}")


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
