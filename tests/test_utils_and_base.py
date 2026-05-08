import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from tests._support import ensure_package, load_module

ensure_package("onecrawler")
ensure_package("onecrawler.crawler")
base_module = load_module("onecrawler.crawler.base", "onecrawler/crawler/base.py")
decorator_module = load_module(
    "tests.loaded_decorator", "onecrawler/utils/decorator.py"
)
writter_module = load_module("tests.loaded_writter", "onecrawler/utils/writter.py")


class Engine(base_module.BaseEngine):
    def __init__(self):
        super().__init__()
        self.started = False
        self.closed = False

    async def start(self):
        self.started = True

    async def close(self):
        self.closed = True

    async def run(self):
        self._ensure_open()
        return "ok"


class UtilsAndBaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_base_engine_context_manager_opens_and_closes(self):
        engine = Engine()

        self.assertTrue(engine.is_closed)
        async with engine:
            self.assertFalse(engine.is_closed)
            self.assertTrue(engine.started)
            self.assertEqual(await engine.run(), "ok")

        self.assertTrue(engine.is_closed)
        self.assertTrue(engine.closed)

    async def test_base_engine_rejects_run_when_closed(self):
        engine = Engine()

        with self.assertRaisesRegex(RuntimeError, "is closed"):
            await engine.run()

    async def test_calculate_execution_time_supports_sync_functions(self):
        elapsed, result = await decorator_module.calculate_execution_time(
            lambda x: x + 1, 2
        )

        self.assertGreaterEqual(elapsed, 0)
        self.assertEqual(result, 3)

    async def test_calculate_execution_time_supports_async_functions(self):
        async def work():
            await asyncio.sleep(0)
            return "done"

        elapsed, result = await decorator_module.calculate_execution_time(work)

        self.assertGreaterEqual(elapsed, 0)
        self.assertEqual(result, "done")

    async def test_save_json_writes_utf8_json(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "data.json"

            writter_module.save_json({"name": "Onecrawler"}, str(target))

            self.assertEqual(
                json.loads(target.read_text(encoding="utf-8")), {"name": "Onecrawler"}
            )


if __name__ == "__main__":
    unittest.main()
