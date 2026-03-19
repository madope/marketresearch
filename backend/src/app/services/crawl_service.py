from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from bs4 import BeautifulSoup

from app.services.llm_client import LLMClient
from app.services.page_fetch_service import PageFetchService


PriceRow = dict[str, Any]
MarkdownPriceExtractor = Callable[[dict[str, object], dict[str, object], str, str], PriceRow | None]


class PriceCrawlerService:
    def __init__(
        self,
        page_fetch_service: PageFetchService | None = None,
        markdown_price_extractor: MarkdownPriceExtractor | None = None,
    ) -> None:
        self.page_fetch_service = page_fetch_service or PageFetchService()
        self.markdown_price_extractor = markdown_price_extractor or self._extract_price_from_markdown

    def crawl_prices(
        self,
        products: list[dict[str, object]],
        platforms: list[dict[str, object]],
        product_platforms: list[dict[str, object]] | None = None,
        max_rounds: int = 3,
    ) -> list[PriceRow]:
        records: list[PriceRow] = []
        if product_platforms:
            product_platform_pairs: list[tuple[dict[str, object], list[dict[str, object]]]] = []
            for mapping in product_platforms:
                product_name = str(mapping["product_name"])
                product = next(
                    (item for item in products if str(item["product_name"]) == product_name),
                    {"product_name": product_name, "source_type": "user_specified", "input_order": len(product_platform_pairs) + 1},
                )
                product_platform_pairs.append((product, list(mapping.get("platforms", []))))
        else:
            product_platform_pairs = [(product, platforms) for product in products]

        for product, product_platform_list in product_platform_pairs:
            records.extend(self.crawl_product_prices(product, product_platform_list, max_rounds=max_rounds))
        return records

    def crawl_product_prices(
        self,
        product: dict[str, object],
        platforms: list[dict[str, object]],
        max_rounds: int = 3,
    ) -> list[PriceRow]:
        records: list[PriceRow] = []
        for platform in platforms:
            product_url = str(
                platform.get("platform_url", f"https://{platform['platform_domain']}/search/{product['input_order']}")
            )
            page_result = self.page_fetch_service.fetch_page(product_url)
            if page_result["status"] != "success":
                records.append(
                    self._build_empty_price_record(
                        product=product,
                        platform=platform,
                        product_url=str(page_result["final_url"]),
                        source="playwright_fetch_failed",
                        notes=str(page_result.get("error_message") or "网页抓取失败"),
                        attempt_count=max_rounds,
                    )
                )
                continue

            extracted = self.markdown_price_extractor(
                product,
                platform,
                str(page_result["markdown"]),
                str(page_result["final_url"]),
            )
            if extracted is None:
                records.append(
                    self._build_empty_price_record(
                        product=product,
                        platform=platform,
                        product_url=str(page_result["final_url"]),
                        source="markdown_llm_unpriced",
                        notes="抓到网页但未识别出价格",
                        attempt_count=1,
                        markdown_excerpt=str(page_result["markdown"])[:1000],
                    )
                )
                continue

            extracted.setdefault("attempt_count", 1)
            extracted.setdefault("source", "markdown_llm_price")
            extracted.setdefault("markdown_excerpt", str(page_result["markdown"])[:1000])
            records.append(extracted)
        return records

    def _extract_price_from_markdown(
        self,
        product: dict[str, object],
        platform: dict[str, object],
        markdown: str,
        product_url: str,
    ) -> PriceRow | None:
        client = LLMClient()
        fallback = {
            "recognized": False,
            "raw_title": str(product["product_name"]),
            "spec_text": "",
            "currency": "CNY",
            "raw_price": None,
            "normalized_price": None,
            "price_unit": None,
            "confidence_score": 0.0,
            "notes": "抓到网页但未识别出价格",
        }
        result = client.generate_json(
            f"""
你是价格抽取节点。
商品: {product}
平台: {platform}
页面 Markdown:
{markdown[:12000]}

任务:
从页面内容中提取当前商品价格。
如果没有明确价格，recognized 返回 false，其余价格字段返回 null。

返回 JSON:
{{
  "recognized": true | false,
  "raw_title": "string",
  "spec_text": "string",
  "currency": "CNY",
  "raw_price": 123.45 | null,
  "normalized_price": 123.45 | null,
  "price_unit": "件" | null,
  "confidence_score": 0.0,
  "notes": "string"
}}
""",
            fallback=fallback,
        ).value
        if not result.get("recognized"):
            return None
        return {
            "product_name": str(product["product_name"]),
            "platform_name": str(platform["platform_name"]),
            "platform_domain": str(platform["platform_domain"]),
            "product_url": product_url,
            "raw_title": str(result.get("raw_title") or product["product_name"]),
            "spec_text": str(result.get("spec_text") or ""),
            "currency": str(result.get("currency") or "CNY"),
            "raw_price": result.get("raw_price"),
            "normalized_price": result.get("normalized_price"),
            "price_unit": result.get("price_unit"),
            "confidence_score": float(result.get("confidence_score") or 0.0),
            "is_outlier": False,
            "source": "markdown_llm_price",
            "notes": str(result.get("notes") or ""),
        }

    def _build_empty_price_record(
        self,
        *,
        product: dict[str, object],
        platform: dict[str, object],
        product_url: str,
        source: str,
        notes: str,
        attempt_count: int,
        markdown_excerpt: str = "",
    ) -> PriceRow:
        return {
            "product_name": str(product["product_name"]),
            "platform_name": str(platform["platform_name"]),
            "platform_domain": str(platform["platform_domain"]),
            "product_url": product_url,
            "raw_title": str(product["product_name"]),
            "spec_text": "",
            "currency": "CNY",
            "raw_price": None,
            "normalized_price": None,
            "price_unit": None,
            "confidence_score": 0.0,
            "is_outlier": False,
            "attempt_count": attempt_count,
            "source": source,
            "notes": notes,
            "markdown_excerpt": markdown_excerpt,
        }

    def extract_price_from_html(
        self,
        html: str,
        product: dict[str, object],
        platform: dict[str, object],
        product_url: str,
    ) -> PriceRow:
        soup = BeautifulSoup(html, "html.parser")
        price_node = soup.select_one(".price, .sales-price, [data-price]")
        price_source = price_node.get_text(" ", strip=True) if price_node else soup.get_text(" ", strip=True)
        price_match = re.search(r"(\d+(?:\.\d{1,2})?)", price_source)
        normalized_price = float(price_match.group(1)) if price_match else None
        title_node = soup.select_one(".sku-name, .title, h1")
        unit_node = soup.select_one(".unit")

        return {
            "product_name": str(product["product_name"]),
            "platform_name": str(platform["platform_name"]),
            "platform_domain": str(platform["platform_domain"]),
            "product_url": product_url,
            "raw_title": title_node.get_text(strip=True) if title_node else str(product["product_name"]),
            "spec_text": "默认规格",
            "currency": "CNY",
            "raw_price": normalized_price,
            "normalized_price": normalized_price,
            "price_unit": unit_node.get_text(strip=True) if unit_node else "件",
            "confidence_score": 0.88 if price_match else 0.5,
            "is_outlier": False,
            "attempt_count": 1,
            "source": "html_fetch",
        }
