import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import httpx

from app.models import Proxy as ProxyModel


@dataclass
class ProxyConfig:
    server: str
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: str = "http"

    def to_playwright_dict(self) -> Dict[str, Any]:
        """Convert to Playwright proxy format"""
        result = {"server": self.server}
        if self.username and self.password:
            result["username"] = self.username
            result["password"] = self.password
        return result

    def to_httpx_dict(self) -> Dict[str, Any]:
        """Convert to httpx proxy format"""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        else:
            auth = ""
        return {"proxy": f"{self.proxy_type}://{auth}{self.server}"}


class ProxyValidator:
    def __init__(self, test_url: str = "https://www.google.com", timeout: int = 10):
        self.test_url = test_url
        self.timeout = timeout

    async def validate(self, proxy: ProxyConfig) -> tuple[bool, Optional[float]]:
        """Validate proxy works and measure latency"""
        try:
            proxies = proxy.to_httpx_dict()
            async with httpx.AsyncClient(proxies=proxies, timeout=self.timeout) as client:
                response = await client.get(self.test_url)
                return True, response.elapsed.total_seconds() * 1000
        except Exception:
            return False, None


class ProxyManager:
    def __init__(self):
        self._proxies: List[ProxyConfig] = []
        self._validator = ProxyValidator()

    def add_proxy(self, proxy: ProxyConfig):
        """Add a proxy to the manager"""
        self._proxies.append(proxy)

    def add_from_model(self, proxy_model: ProxyModel) -> ProxyConfig:
        """Add a proxy from database model"""
        # Build server address
        server = f"{proxy_model.host}:{proxy_model.port}"

        proxy = ProxyConfig(
            server=server,
            username=proxy_model.username,
            password=proxy_model.password,
            proxy_type=proxy_model.proxy_type,
        )
        self.add_proxy(proxy)
        return proxy

    def get_random(self) -> Optional[ProxyConfig]:
        """Get a random proxy from the pool"""
        if not self._proxies:
            return None
        import random
        return random.choice(self._proxies)

    def get_all(self) -> List[ProxyConfig]:
        """Get all proxies"""
        return list(self._proxies)

    async def validate_all(self) -> List[tuple[ProxyConfig, bool, Optional[float]]]:
        """Validate all proxies"""
        results = []
        for proxy in self._proxies:
            works, latency = await self._validator.validate(proxy)
            results.append((proxy, works, latency))
        return results

    def clear(self):
        """Clear all proxies"""
        self._proxies.clear()

    @property
    def count(self) -> int:
        return len(self._proxies)


# Global proxy manager instance
_proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager() -> ProxyManager:
    """Get the global proxy manager instance"""
    global _proxy_manager
    if not _proxy_manager:
        _proxy_manager = ProxyManager()
    return _proxy_manager
