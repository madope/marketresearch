from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


PlatformRow = dict[str, str | int]
SearchProvider = Callable[[str, int], list[PlatformRow]]
SearchHtmlProvider = Callable[[str, int], str | None]


class PlatformDiscoveryService:
    def __init__(
        self,
        search_provider: SearchProvider | None = None,
        search_html_provider: SearchHtmlProvider | None = None,
    ) -> None:
        self.search_provider = search_provider or self._default_search_provider
        self.search_html_provider = search_html_provider or self._default_search_html_provider
        self._fallback_platforms = [
            {"platform_name": "京东", "platform_domain": "jd.com", "platform_type": "marketplace"},
            {"platform_name": "淘宝", "platform_domain": "taobao.com", "platform_type": "marketplace"},
            {"platform_name": "天猫", "platform_domain": "tmall.com", "platform_type": "marketplace"},
            {"platform_name": "拼多多", "platform_domain": "pinduoduo.com", "platform_type": "marketplace"},
            {"platform_name": "苏宁易购", "platform_domain": "suning.com", "platform_type": "marketplace"},
            {"platform_name": "唯品会", "platform_domain": "vip.com", "platform_type": "marketplace"},
            {"platform_name": "当当", "platform_domain": "dangdang.com", "platform_type": "marketplace"},
            {"platform_name": "得物", "platform_domain": "dewu.com", "platform_type": "marketplace"},
            {"platform_name": "考拉海购", "platform_domain": "kaola.com", "platform_type": "marketplace"},
            {"platform_name": "小红书", "platform_domain": "xiaohongshu.com", "platform_type": "social_commerce"},
        ]

    def discover_platforms(
        self,
        product_names: list[str],
        max_platforms: int = 5,
        max_rounds: int = 3,
    ) -> list[PlatformRow]:
        deduped: dict[str, PlatformRow] = {}

        for round_number in range(1, max_rounds + 1):
            for product_name in product_names:
                html = self.search_html_provider(product_name, round_number)
                candidates = self.parse_search_result_html(html) if html else self.search_provider(product_name, round_number)
                for candidate in candidates:
                    domain = str(candidate["platform_domain"])
                    if domain not in deduped:
                        deduped[domain] = {
                            "platform_name": str(candidate["platform_name"]),
                            "platform_domain": domain,
                            "discover_round": round_number,
                            "platform_type": str(candidate.get("platform_type", "marketplace")),
                            "source": str(candidate.get("source", "structured_search")),
                        }
                if len(deduped) >= max_platforms:
                    return list(deduped.values())[:max_platforms]

        for fallback in self._fallback_platforms:
            domain = str(fallback["platform_domain"])
            if domain not in deduped:
                deduped[domain] = {
                    "platform_name": str(fallback["platform_name"]),
                    "platform_domain": domain,
                    "discover_round": max_rounds,
                    "platform_type": str(fallback["platform_type"]),
                    "source": "fallback_seed",
                }
            if len(deduped) >= max_platforms:
                break

        return list(deduped.values())[:max_platforms]

    def _default_search_provider(self, product_name: str, round_number: int) -> list[PlatformRow]:
        rotation = self._fallback_platforms[round_number - 1 :] + self._fallback_platforms[: round_number - 1]
        return rotation[: min(3, len(rotation))]

    def _default_search_html_provider(self, product_name: str, round_number: int) -> str | None:
        query = {
            1: f"{product_name} 电商 平台 价格",
            2: f"{product_name} 京东 淘宝 天猫 拼多多",
            3: f"{product_name} 哪里可以买",
        }.get(round_number, product_name)
        try:
            response = httpx.get(
                "https://www.bing.com/search",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0 MarketResearchBot/0.1"},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.text
        except httpx.HTTPError:
            return None

    def parse_search_result_html(self, html: str) -> list[PlatformRow]:
        soup = BeautifulSoup(html, "html.parser")
        deduped: dict[str, PlatformRow] = {}
        domain_name_map = {
            "jd.com": "京东",
            "taobao.com": "淘宝",
            "tmall.com": "天猫",
            "yangkeduo.com": "拼多多",
            "pinduoduo.com": "拼多多",
            "suning.com": "苏宁易购",
        }

        for anchor in soup.find_all("a", href=True):
            parsed = urlparse(anchor["href"])
            hostname = parsed.hostname or ""
            matched_domain = next((domain for domain in domain_name_map if hostname.endswith(domain)), None)
            if not matched_domain or matched_domain in deduped:
                continue

            deduped[matched_domain] = {
                "platform_name": domain_name_map[matched_domain],
                "platform_domain": "pinduoduo.com" if matched_domain == "yangkeduo.com" else matched_domain,
                "discover_round": 1,
                "platform_type": "marketplace",
                "source": "html_search",
            }

        return list(deduped.values())
