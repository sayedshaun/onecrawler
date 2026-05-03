from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LaunchSettings:
    headless: bool = True
    slow_mo: int = 0

    args: List[str] = field(
        default_factory=lambda: [
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
        ]
    )

    executable_path: Optional[str] = None
    channel: Optional[str] = None
    env: Optional[Dict[str, str]] = None


@dataclass
class ContextSettings:
    viewport: Optional[Dict[str, int]] = field(
        default_factory=lambda: {"width": 1366, "height": 768}
    )
    screen: Optional[Dict[str, int]] = None
    no_viewport: Optional[bool] = None

    user_agent: Optional[str] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
    locale: str = "en-US"
    timezone_id: str = "Asia/Dhaka"

    geolocation: Optional[Dict[str, float]] = None
    permissions: Optional[List[str]] = None

    extra_http_headers: Optional[Dict[str, str]] = None

    java_script_enabled: bool = True
    bypass_csp: bool = True
    ignore_https_errors: bool = True

    offline: bool = False
    storage_state: Optional[str] = None
    base_url: Optional[str] = None


@dataclass
class ProxySettings:
    server: str
    username: Optional[str] = None
    password: Optional[str] = None


@dataclass
class RuntimeSettings:
    wait_until: str = "networkidle"
    timeout: int = 30000
    action_timeout: int = 30000
    navigation_timeout: int = 30000

    max_retries: int = 2
    retry_delay: float = 1.0


@dataclass
class BrowserSettings:
    user_data_dir: str = ".temp/browser_profile"

    launch: LaunchSettings = field(default_factory=LaunchSettings)
    context: ContextSettings = field(default_factory=ContextSettings)
    runtime: RuntimeSettings = field(default_factory=RuntimeSettings)
    proxy: Optional[ProxySettings] = None
