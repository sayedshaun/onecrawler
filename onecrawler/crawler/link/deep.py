import asyncio
import tempfile
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from .helper import human_delay, human_scroll, wildcard_link_match


async def detect_page_type(page: object) -> str:
    try:
        # pagination detection
        pagination_links = await page.eval_on_selector_all(
            "a",
            """els => els.map(e => e.href).filter(h =>
                h.includes('page=') ||
                h.match(/\\/page\\/\\d+/) ||
                h.toLowerCase().includes('next')
            )""",
        )

        if len(pagination_links) >= 2:
            return "pagination"

        # infinite scroll detection
        h1 = await page.evaluate("document.body.scrollHeight")

        await page.mouse.wheel(0, 1500)
        await asyncio.sleep(1)

        h2 = await page.evaluate("document.body.scrollHeight")

        if h2 > h1:
            return "infinite"

        return "static"

    except Exception:
        return "static"


async def smart_collect_links(page: object, page_type: str) -> list[str]:
    collected = set()

    async def extract():
        links = await page.eval_on_selector_all(
            "a", "els => els.map(e => e.href).filter(Boolean)"
        )
        collected.update(links)

    if page_type == "pagination":
        await extract()

    elif page_type == "infinite":
        last_count = 0

        for _ in range(10):  # safety cap
            await page.mouse.wheel(0, 1200)
            await asyncio.sleep(0.8)

            await extract()

            if len(collected) == last_count:
                break

            last_count = len(collected)

    else:
        await human_scroll(page, max_scrolls=3)
        await extract()

    return list(collected)


async def bfs_link_extractor(
    base_url: str,
    num_links: int = 50,
    include_pattern: list[str] | None = None,
    concurrency: int = 5,
):
    visited = set()
    seen = set()
    results = []

    queue = asyncio.Queue()
    await queue.put(base_url)

    parsed = urlparse(base_url)
    base_prefix = f"{parsed.scheme}://{parsed.netloc}"

    semaphore = asyncio.Semaphore(concurrency)

    async def worker(page):
        nonlocal results

        while True:
            if len(results) >= num_links:
                return

            try:
                url = await asyncio.wait_for(queue.get(), timeout=3)
            except asyncio.TimeoutError:
                return

            if url in visited:
                queue.task_done()
                continue

            visited.add(url)

            async with semaphore:
                try:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")

                    await human_delay()

                    # AUTO-DETECT PAGE TYPE
                    page_type = await detect_page_type(page)

                    # SMART LINK COLLECTION
                    links = await smart_collect_links(page, page_type)

                    for link in links:
                        if len(results) >= num_links:
                            break

                        if link in seen:
                            continue

                        if not wildcard_link_match(link, base_prefix, include_pattern):
                            continue

                        seen.add(link)
                        results.append(link)

                        if link not in visited:
                            await queue.put(link)

                except Exception as e:
                    raise RuntimeError(f"Error processing {url}: {e}")

            queue.task_done()
            await human_delay()

    async with async_playwright() as p:
        with tempfile.TemporaryDirectory() as d:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=d,
                headless=True,
                viewport={"width": 1366, "height": 768},
                locale="en-US",
                timezone_id="Asia/Dhaka",
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ],
            )

            pages = [await context.new_page() for _ in range(concurrency)]
            tasks = [asyncio.create_task(worker(page)) for page in pages]
            await asyncio.gather(*tasks, return_exceptions=True)
            await context.close()

    return results
