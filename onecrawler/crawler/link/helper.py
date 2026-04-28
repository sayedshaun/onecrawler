import asyncio
import random
from urllib.parse import unquote


async def human_delay(min_s=0.3, max_s=1.2):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def human_scroll(page, max_scrolls=3):
    try:
        for _ in range(max_scrolls):
            await page.mouse.wheel(0, random.randint(400, 800))
            await asyncio.sleep(random.uniform(0.2, 0.6))
    except Exception as e:
        print(f"[ERROR] Scroll: {e}")


def normalize(text: str) -> str:
    
    return unquote(text).lower().strip().rstrip("/")
