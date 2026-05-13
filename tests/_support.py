from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def ensure_package(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    package_path = ROOT.joinpath(*name.split("."))
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = [str(package_path)] if package_path.is_dir() else []
        sys.modules[name] = module
    elif hasattr(module, "__path__") and package_path.is_dir():
        path = str(package_path)
        if path not in module.__path__:
            module.__path__.append(path)
    return module


def load_module(name: str, relative_path: str):
    module = sys.modules.get(name)
    if module is not None:
        return module

    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {name} from {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_settings_modules():
    ensure_package("onecrawler")
    ensure_package("onecrawler.settings")
    ensure_package("onecrawler.proxy")

    # Load proxy modules first
    load_module(
        "onecrawler.settings.proxy",
        "onecrawler/settings/proxy.py",
    )
    load_module(
        "onecrawler.proxy.pool",
        "onecrawler/proxy/pool.py",
    )
    load_module(
        "onecrawler.proxy",
        "onecrawler/proxy/__init__.py",
    )

    # Then load other settings modules
    browser = load_module(
        "onecrawler.settings.browser",
        "onecrawler/settings/browser.py",
    )

    genai = load_module(
        "onecrawler.settings.genai",
        "onecrawler/settings/genai.py",
    )

    load_module(
        "onecrawler.settings.simulation",
        "onecrawler/settings/simulation.py",
    )

    crawler = load_module(
        "onecrawler.settings.crawler",
        "onecrawler/settings/crawler.py",
    )

    return browser, genai, crawler


def load_link_modules():
    ensure_package("onecrawler")
    ensure_package("onecrawler.settings")
    ensure_package("onecrawler.crawler")
    ensure_package("onecrawler.crawler.link")
    load_module("onecrawler.settings.simulation", "onecrawler/settings/simulation.py")
    helper = load_module(
        "onecrawler.crawler.link.helper", "onecrawler/crawler/link/helper.py"
    )
    deep = load_module(
        "onecrawler.crawler.link.deep", "onecrawler/crawler/link/deep.py"
    )
    return helper, deep


def install_curl_cffi_stub() -> None:
    if "curl_cffi.requests" in sys.modules:
        return

    curl_cffi = types.ModuleType("curl_cffi")
    requests = types.ModuleType("curl_cffi.requests")

    class AsyncSession:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        async def close(self):
            return None

    requests.AsyncSession = AsyncSession
    curl_cffi.requests = requests
    sys.modules["curl_cffi"] = curl_cffi
    sys.modules["curl_cffi.requests"] = requests


def install_trafilatura_stub() -> None:
    if "trafilatura" in sys.modules:
        return

    trafilatura = types.ModuleType("trafilatura")

    def fetch_url(*args, **kwargs):
        return None

    def extract(*args, **kwargs):
        return None

    trafilatura.fetch_url = fetch_url
    trafilatura.extract = extract
    sys.modules["trafilatura"] = trafilatura
