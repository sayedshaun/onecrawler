from dataclasses import dataclass
from typing import Dict, Optional
from urllib.parse import quote, urlsplit, urlunsplit


@dataclass
class ProxySettings:
    """Configuration for a single proxy server.

    Attributes:
        server (str): The proxy server URL (e.g., "http://myproxy.com:8080").
        username (Optional[str]): Username for proxy authentication.
        password (Optional[str]): Password for proxy authentication.
    """

    server: str
    username: Optional[str] = None
    password: Optional[str] = None

    def as_playwright(self) -> Dict[str, str]:
        """Converts proxy settings to a dictionary format expected by Playwright.

        Returns:
            Dict[str, str]: A dictionary with 'server', 'username', and 'password'.
        """
        proxy = {"server": self.server}
        if self.username:
            proxy["username"] = self.username
        if self.password:
            proxy["password"] = self.password
        return proxy

    def as_requests_proxies(self) -> Dict[str, str]:
        """Converts proxy settings to a dictionary format expected by the requests library.

        Returns:
            Dict[str, str]: A dictionary with 'http' and 'https' keys mapping to the proxy URL.
        """
        server = self._server_with_auth()
        return {"http": server, "https": server}

    def _server_with_auth(self) -> str:
        """Constructs a proxy server URL that includes authentication credentials.

        Returns:
            str: The proxy URL with username and password encoded (if present).
        """
        if not self.username:
            return self.server

        parsed = urlsplit(self.server)
        if "@" in parsed.netloc:
            return self.server

        username = quote(self.username, safe="")
        password = quote(self.password or "", safe="")
        credentials = f"{username}:{password}"
        return urlunsplit(
            (
                parsed.scheme,
                f"{credentials}@{parsed.netloc}",
                parsed.path,
                parsed.query,
                parsed.fragment,
            )
        )
