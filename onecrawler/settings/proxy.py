from dataclasses import dataclass
from typing import Dict, Optional
from urllib.parse import quote, urlsplit, urlunsplit


@dataclass
class ProxySettings:
    server: str
    username: Optional[str] = None
    password: Optional[str] = None

    def as_playwright(self) -> Dict[str, str]:
        proxy = {"server": self.server}
        if self.username:
            proxy["username"] = self.username
        if self.password:
            proxy["password"] = self.password
        return proxy

    def as_requests_proxies(self) -> Dict[str, str]:
        server = self._server_with_auth()
        return {"http": server, "https": server}

    def _server_with_auth(self) -> str:
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
