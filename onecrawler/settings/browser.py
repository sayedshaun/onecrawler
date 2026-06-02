from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .proxy import ProxySettings


@dataclass
class BrowserSettings:
    """Settings for a browser instance.

    Attributes:
        user_data_dir (str): Directory for browser profile data.
        proxy (Optional[ProxySettings]): Proxy configuration.
        viewport (Optional[Dict[str, int]]): The default viewport size for each page.
        screen (Optional[Dict[str, int]]): The screen size.
        no_viewport (Optional[bool]): Whether to disable the default viewport.
        user_agent (Optional[str]): The user agent string to use.
        locale (str): The locale (e.g., "en-US").
        timezone_id (str): The timezone ID (e.g., "Asia/Dhaka").
        geolocation (Optional[Dict[str, float]]): The geolocation coordinates.
        permissions (Optional[List[str]]): List of permissions to grant (e.g., ["geolocation"]).
        extra_http_headers (Optional[Dict[str, str]]): Additional HTTP headers to send with every request.
        java_script_enabled (bool): Whether to enable JavaScript.
        bypass_csp (bool): Whether to bypass Content Security Policy.
        ignore_https_errors (bool): Whether to ignore HTTPS errors.
        offline (bool): Whether to simulate being offline.
        storage_state (Optional[str]): Path to a file with the storage state (cookies, localStorage).
        base_url (Optional[str]): Base URL for navigation.
        headless (bool): Whether to run the browser in headless mode.
        slow_mo (int): Slows down Playwright operations by the specified amount of milliseconds.
        args (List[str]): Additional arguments to pass to the browser instance.
        executable_path (Optional[str]): Path to a browser executable to use instead of the bundled one.
        channel (Optional[str]): Browser distribution channel (e.g., "chrome", "msedge").
        env (Optional[Dict[str, str]]): Environment variables that will be visible to the browser.
        wait_until (str): When to consider navigation finished (e.g., "domcontentloaded").
        timeout (int): Timeout for browser operations in milliseconds.
    """

    user_data_dir: str = ".chrome"
    proxy: Optional[ProxySettings] = None

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

    wait_until: str = "domcontentloaded"
    timeout: int = 30000
