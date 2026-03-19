from app.services.crawl_service import PriceCrawlerService
from app.services.page_fetch_service import PageFetchService
from app.services.discovery_service import PlatformDiscoveryService
from app.services.normalize_service import normalize_price_records


def test_platform_discovery_returns_at_least_five_unique_platforms() -> None:
    service = PlatformDiscoveryService()

    platforms = service.discover_platforms(
        ["宠物烘干箱 标准款", "宠物烘干箱 Pro"],
        max_platforms=5,
        max_rounds=3,
    )

    assert len(platforms) >= 5
    assert len({platform["platform_domain"] for platform in platforms}) == len(platforms)


def test_platform_discovery_retries_before_fallback() -> None:
    attempts: list[int] = []

    def search_stub(_product_name: str, round_number: int):
        attempts.append(round_number)
        return []

    service = PlatformDiscoveryService(search_provider=search_stub)
    platforms = service.discover_platforms(["智能猫砂盆"], max_platforms=5, max_rounds=3)

    assert attempts == [1, 2, 3]
    assert len(platforms) == 5


def test_platform_discovery_parses_search_result_html() -> None:
    service = PlatformDiscoveryService()
    html = """
    <html><body>
      <a href="https://item.jd.com/1001.html">京东商品</a>
      <a href="https://detail.tmall.com/item.htm?id=2002">天猫商品</a>
      <a href="https://www.example.com/other">其他站点</a>
    </body></html>
    """

    platforms = service.parse_search_result_html(html)

    assert [platform["platform_domain"] for platform in platforms] == ["jd.com", "tmall.com"]
    assert platforms[0]["platform_name"] == "京东"


def test_platform_discovery_uses_html_provider_before_fallback() -> None:
    def html_provider(_query: str, round_number: int) -> str:
        if round_number == 1:
            return """
            <a href="https://item.jd.com/1001.html">京东</a>
            <a href="https://detail.tmall.com/item.htm?id=2002">天猫</a>
            """
        return """
        <a href="https://www.taobao.com/item/3">淘宝</a>
        <a href="https://mobile.yangkeduo.com/goods.html?goods_id=4">拼多多</a>
        <a href="https://product.suning.com/5.html">苏宁</a>
        """

    service = PlatformDiscoveryService(search_html_provider=html_provider)
    platforms = service.discover_platforms(["宠物烘干箱"], max_platforms=5, max_rounds=3)

    assert [platform["platform_domain"] for platform in platforms] == [
        "jd.com",
        "tmall.com",
        "taobao.com",
        "pinduoduo.com",
        "suning.com",
    ]


def test_price_crawler_generates_matrix_for_products_and_platforms() -> None:
    crawler = PriceCrawlerService()
    records = crawler.crawl_prices(
        products=[
            {"product_name": "iPhone 16", "source_type": "user_specified", "input_order": 1},
            {"product_name": "华为 Mate 70", "source_type": "user_specified", "input_order": 2},
        ],
        platforms=[
            {"platform_name": "京东", "platform_domain": "jd.com", "discover_round": 1, "platform_type": "marketplace"},
            {"platform_name": "淘宝", "platform_domain": "taobao.com", "discover_round": 1, "platform_type": "marketplace"},
        ],
        max_rounds=3,
    )

    assert len(records) == 4
    assert all("normalized_price" in record for record in records)


def test_price_crawler_uses_markdown_price_extractor_result() -> None:
    class StubPageFetchService:
        def fetch_page(self, url: str) -> dict[str, object]:
            return {
                "status": "success",
                "final_url": url,
                "html": "<h1>iPhone 16</h1>",
                "markdown": "# iPhone 16\n\n价格 5999 元",
                "error_message": None,
            }

    def extractor(product: dict[str, object], platform: dict[str, object], markdown: str, product_url: str):
        return {
            "product_name": str(product["product_name"]),
            "platform_name": str(platform["platform_name"]),
            "platform_domain": str(platform["platform_domain"]),
            "product_url": product_url,
            "raw_title": "iPhone 16",
            "spec_text": "128G",
            "currency": "CNY",
            "raw_price": 5999,
            "normalized_price": 5999,
            "price_unit": "件",
            "confidence_score": 0.92,
            "is_outlier": False,
        }

    crawler = PriceCrawlerService(
        page_fetch_service=StubPageFetchService(),
        markdown_price_extractor=extractor,
    )
    records = crawler.crawl_prices(
        products=[{"product_name": "iPhone 16", "source_type": "user_specified", "input_order": 1}],
        platforms=[{"platform_name": "京东", "platform_domain": "jd.com", "platform_url": "https://jd.com/item/1"}],
        max_rounds=1,
    )

    assert records[0]["confidence_score"] == 0.92
    assert records[0]["normalized_price"] == 5999


def test_price_crawler_extracts_price_from_html() -> None:
    crawler = PriceCrawlerService()
    html = """
    <html><body>
      <div class="sku-name">电动牙刷旗舰版</div>
      <span class="price">299.50</span>
      <span class="unit">件</span>
    </body></html>
    """

    record = crawler.extract_price_from_html(
        html=html,
        product={"product_name": "电动牙刷", "input_order": 1},
        platform={"platform_name": "京东", "platform_domain": "jd.com"},
        product_url="https://jd.com/item/1",
    )

    assert record["normalized_price"] == 299.5
    assert record["raw_title"] == "电动牙刷旗舰版"


def test_price_crawler_passes_markdown_excerpt_to_empty_record() -> None:
    class StubPageFetchService:
        def fetch_page(self, url: str) -> dict[str, object]:
            return {
                "status": "success",
                "final_url": url,
                "html": "<h1>华为 Mate 70</h1>",
                "markdown": "# 华为 Mate 70\n\n价格待咨询",
                "error_message": None,
            }

    crawler = PriceCrawlerService(
        page_fetch_service=StubPageFetchService(),
        markdown_price_extractor=lambda *_args: None,
    )
    records = crawler.crawl_prices(
        products=[{"product_name": "华为 Mate 70", "source_type": "user_specified", "input_order": 1}],
        platforms=[{"platform_name": "京东", "platform_domain": "jd.com", "platform_url": "https://jd.com/item/1"}],
        max_rounds=1,
    )

    assert "华为 Mate 70" in records[0]["markdown_excerpt"]
    assert records[0]["notes"] == "抓到网页但未识别出价格"


def test_price_crawler_uses_platform_url_for_page_fetch() -> None:
    captured_urls: list[str] = []

    class StubPageFetchService:
        def fetch_page(self, url: str) -> dict[str, object]:
            captured_urls.append(url)
            return {
                "status": "success",
                "final_url": url,
                "html": "<h1>宠物烘干箱</h1>",
                "markdown": "# 宠物烘干箱\n\n价格 1299 元",
                "error_message": None,
            }

    crawler = PriceCrawlerService(
        page_fetch_service=StubPageFetchService(),
        markdown_price_extractor=lambda product, platform, markdown, product_url: {
            "product_name": str(product["product_name"]),
            "platform_name": str(platform["platform_name"]),
            "platform_domain": str(platform["platform_domain"]),
            "product_url": product_url,
            "raw_title": "宠物烘干箱",
            "spec_text": "",
            "currency": "CNY",
            "raw_price": 1299,
            "normalized_price": 1299,
            "price_unit": "件",
            "confidence_score": 0.9,
            "is_outlier": False,
        },
    )
    records = crawler.crawl_prices(
        products=[{"product_name": "宠物烘干箱", "source_type": "category_inferred", "input_order": 1}],
        platforms=[
            {
                "platform_name": "京东",
                "platform_domain": "jd.com",
                "platform_url": "https://item.jd.com/1001.html",
                "platform_summary": "综合电商平台",
                "discover_round": 1,
                "platform_type": "marketplace",
            }
        ],
        max_rounds=3,
    )

    assert captured_urls == ["https://item.jd.com/1001.html"]
    assert records[0]["product_url"] == "https://item.jd.com/1001.html"


def test_price_crawler_uses_product_platform_groups() -> None:
    crawler = PriceCrawlerService()
    records = crawler.crawl_prices(
        products=[],
        platforms=[],
        product_platforms=[
            {
                "product_name": "产品A",
                "platforms": [
                    {
                        "platform_name": "平台A1",
                        "platform_domain": "a1.com",
                        "platform_url": "https://a1.com/item/1",
                        "discover_round": 1,
                        "platform_type": "marketplace",
                    },
                    {
                        "platform_name": "平台A2",
                        "platform_domain": "a2.com",
                        "platform_url": "https://a2.com/item/2",
                        "discover_round": 1,
                        "platform_type": "marketplace",
                    },
                ],
            },
            {
                "product_name": "产品B",
                "platforms": [
                    {
                        "platform_name": "平台B1",
                        "platform_domain": "b1.com",
                        "platform_url": "https://b1.com/item/1",
                        "discover_round": 1,
                        "platform_type": "marketplace",
                    }
                ],
            },
        ],
        max_rounds=1,
    )

    assert len(records) == 3
    assert [record["product_name"] for record in records] == ["产品A", "产品A", "产品B"]


def test_page_fetch_service_converts_html_to_markdown() -> None:
    markdown = PageFetchService.html_to_markdown(
        """
        <html><body>
          <h1>电动牙刷</h1>
          <p>这是商品详情。</p>
          <ul><li>续航 30 天</li></ul>
        </body></html>
        """
    )

    assert "# 电动牙刷" in markdown
    assert "这是商品详情。" in markdown
    assert "- 续航 30 天" in markdown


def test_price_crawler_keeps_record_when_markdown_has_no_price() -> None:
    class StubPageFetchService:
        def fetch_page(self, url: str) -> dict[str, object]:
            return {
                "status": "success",
                "final_url": url,
                "html": "<h1>电动牙刷</h1><p>暂无价格</p>",
                "markdown": "# 电动牙刷\n\n暂无价格",
                "error_message": None,
            }

    def extractor(product: dict[str, object], platform: dict[str, object], markdown: str, product_url: str):
        return None

    crawler = PriceCrawlerService(
        page_fetch_service=StubPageFetchService(),
        markdown_price_extractor=extractor,
    )
    records = crawler.crawl_prices(
        products=[{"product_name": "电动牙刷", "source_type": "category_inferred", "input_order": 1}],
        platforms=[{"platform_name": "京东", "platform_domain": "jd.com", "platform_url": "https://item.jd.com/1"}],
        max_rounds=1,
    )

    assert len(records) == 1
    assert records[0]["product_url"] == "https://item.jd.com/1"
    assert records[0]["normalized_price"] is None
    assert records[0]["source"] == "markdown_llm_unpriced"
    assert records[0]["notes"] == "抓到网页但未识别出价格"


def test_price_crawler_keeps_record_when_page_fetch_fails() -> None:
    class StubPageFetchService:
        def fetch_page(self, url: str) -> dict[str, object]:
            return {
                "status": "error",
                "final_url": url,
                "html": "",
                "markdown": "",
                "error_message": "browser timeout",
            }

    crawler = PriceCrawlerService(page_fetch_service=StubPageFetchService())
    records = crawler.crawl_prices(
        products=[{"product_name": "电动牙刷", "source_type": "category_inferred", "input_order": 1}],
        platforms=[{"platform_name": "京东", "platform_domain": "jd.com", "platform_url": "https://item.jd.com/1"}],
        max_rounds=1,
    )

    assert len(records) == 1
    assert records[0]["product_url"] == "https://item.jd.com/1"
    assert records[0]["normalized_price"] is None
    assert records[0]["source"] == "playwright_fetch_failed"
    assert records[0]["notes"] == "browser timeout"


def test_normalize_price_records_standardizes_numeric_fields() -> None:
    rows, stats = normalize_price_records(
        [
            {
                "product_name": "电动牙刷",
                "platform_name": "京东",
                "platform_domain": "jd.com",
                "product_url": "https://jd.com/item/1",
                "raw_title": "电动牙刷",
                "spec_text": "默认规格",
                "currency": "CNY",
                "raw_price": "299.50",
                "normalized_price": "299.50",
                "price_unit": "件",
                "confidence_score": "0.83",
                "is_outlier": False,
            }
        ]
    )

    assert rows[0]["raw_price"] == 299.5
    assert rows[0]["normalized_price"] == 299.5
    assert rows[0]["confidence_score"] == 0.83
    assert rows[0]["currency"] == "CNY"
    assert rows[0]["price_unit"] == "件"
    assert stats["input_count"] == 1
    assert stats["final_count"] == 1


def test_normalize_price_records_filters_invalid_rows_and_deduplicates() -> None:
    rows, stats = normalize_price_records(
        [
            {
                "product_name": "电动牙刷",
                "platform_name": "京东",
                "platform_domain": "jd.com",
                "product_url": "https://jd.com/item/1",
                "raw_title": "电动牙刷A",
                "spec_text": "默认规格",
                "currency": "cny",
                "raw_price": "199.00",
                "normalized_price": None,
                "price_unit": "个",
                "confidence_score": "0.72",
                "is_outlier": False,
                "attempt_count": "2",
                "source": "markdown_llm_price",
            },
            {
                "product_name": "电动牙刷",
                "platform_name": "京东",
                "platform_domain": "jd.com",
                "product_url": "https://jd.com/item/1",
                "raw_title": "电动牙刷A-重复",
                "spec_text": "默认规格",
                "currency": "CNY",
                "raw_price": "199.00",
                "normalized_price": "199.00",
                "price_unit": "件",
                "confidence_score": "0.91",
                "is_outlier": False,
                "attempt_count": 1,
                "source": "markdown_llm_price",
            },
            {
                "product_name": "电动牙刷",
                "platform_name": "淘宝",
                "platform_domain": "taobao.com",
                "product_url": "https://taobao.com/item/2",
                "raw_title": "电动牙刷B",
                "spec_text": "默认规格",
                "currency": "CNY",
                "raw_price": None,
                "normalized_price": None,
                "price_unit": None,
                "confidence_score": 0.1,
                "is_outlier": False,
                "source": "markdown_llm_unpriced",
            },
            {
                "product_name": "电动牙刷",
                "platform_name": "拼多多",
                "platform_domain": "pinduoduo.com",
                "product_url": "https://pinduoduo.com/item/3",
                "raw_title": "电动牙刷C",
                "spec_text": "默认规格",
                "currency": "CNY",
                "raw_price": "abc",
                "normalized_price": "abc",
                "price_unit": "台",
                "confidence_score": 0.5,
                "is_outlier": False,
                "source": "markdown_llm_price",
            },
        ]
    )

    assert len(rows) == 1
    assert rows[0]["normalized_price"] == 199.0
    assert rows[0]["raw_price"] == 199.0
    assert rows[0]["price_unit"] == "件"
    assert rows[0]["confidence_score"] == 0.91
    assert rows[0]["attempt_count"] == 1
    assert stats == {
        "input_count": 4,
        "removed_missing_price_count": 1,
        "removed_invalid_format_count": 1,
        "removed_duplicate_count": 1,
        "final_count": 1,
    }
