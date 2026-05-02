from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class BrowserSettings:
    # core behavior
    headless: bool = True
    slow_mo: int = 0

    # profile / persistence
    user_data_dir: str = ".temp/browser_profile"

    # viewport / device emulation
    viewport: Dict[str, int] = field(
        default_factory=lambda: {"width": 1366, "height": 768}
    )
    device_scale_factor: float = 1.0

    # locale / geo
    locale: str = "en-US"
    timezone_id: str = "Asia/Dhaka"

    # identity
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # performance tuning
    ignore_https_errors: bool = True
    java_script_enabled: bool = True
    bypass_csp: bool = True

    # anti-bot / stealth args
    args: List[str] = field(
        default_factory=lambda: [
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
        ]
    )

    # request-level behavior
    wait_until: str = "networkidle"
    timeout: int = 30000

    # optional proxy
    proxy: Optional[Dict[str, str]] = None
