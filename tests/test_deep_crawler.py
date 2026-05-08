import asyncio
import unittest

from tests._support import load_link_modules

_, deep_module = load_link_modules()


class FakePage:
    def __init__(self, links=None):
        self.links = links or []
        self.closed = False
        self.visited = []

    async def goto(self, url, **kwargs):
        self.visited.append((url, kwargs))

    async def eval_on_selector_all(self, selector, script):
        return self.links

    async def close(self):
        self.closed = True


class DeepCrawlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_scheduler_prioritizes_priority_queue_and_deduplicates(self):
        scheduler = deep_module.BFScheduler("https://example.com")

        await scheduler.add("https://example.com/a")
        await scheduler.add("https://example.com/a")
        await scheduler.add("https://example.com/priority", priority=True)

        self.assertEqual(await scheduler.next(), "https://example.com/priority")
        self.assertEqual(await scheduler.next(), "https://example.com")
        self.assertEqual(await scheduler.next(), "https://example.com/a")
        scheduler.mark_visited("https://example.com/a")
        await scheduler.add("https://example.com/a")
        self.assertEqual(await scheduler.next(), None)

    async def test_scheduler_respects_max_queue_size(self):
        scheduler = deep_module.BFScheduler("https://example.com", max_queue_size=1)

        await scheduler.add("https://example.com/ignored")

        self.assertEqual(list(scheduler.queue), ["https://example.com"])

    async def test_link_spider_returns_only_same_prefix_links(self):
        spider = deep_module.LinkSpider("https://example.com")
        page = FakePage(
            [
                "https://example.com/a",
                "https://other.com/b",
                123,
                "mailto:test@example.com",
            ]
        )

        self.assertEqual(await spider.parse(page), ["https://example.com/a"])

    async def test_browser_pool_closes_pages_and_browser(self):
        class Browser:
            def __init__(self):
                self.started = False
                self.closed = False
                self.created = []

            async def start(self):
                self.started = True

            async def new_page(self):
                page = FakePage()
                self.created.append(page)
                return page

            async def close(self):
                self.closed = True

        browser = Browser()
        pool = deep_module.BrowserPool(browser, 2)

        await pool.init()
        await pool.close()

        self.assertTrue(browser.started)
        self.assertTrue(browser.closed)
        self.assertTrue(all(page.closed for page in browser.created))

    async def test_runtime_collects_links_until_limit(self):
        class Pool:
            def __init__(self):
                self.page = FakePage()

            async def acquire(self):
                return self.page

            async def release(self, page):
                return None

        class Spider:
            async def parse(self, page):
                return ["https://example.com/a", "https://example.com/b"]

        runtime = deep_module.BFSRuntime(
            scheduler=deep_module.BFScheduler("https://example.com"),
            pool=Pool(),
            spider=Spider(),
            base_prefix="https://example.com",
            max_links=1,
            include_pattern=None,
            disable_human_behaviors=True,
            concurrency=1,
        )

        result = await asyncio.wait_for(runtime.run(), timeout=1)

        self.assertEqual(result, ["https://example.com/a"])


if __name__ == "__main__":
    unittest.main()
