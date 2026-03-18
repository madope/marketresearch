import pytest
from concurrent.futures import Future

from app.core.config import Settings
from app.services.kimi_client import LLMResult
from app.workflows.research_workflow import (
    _llm_review_price_rows,
    crawl_prices_parallel,
    discover_platforms,
    get_research_graph,
    run_research_workflow,
)


def test_research_graph_returns_invokeable_state_graph() -> None:
    graph = get_research_graph()

    result = graph.invoke({"prompt": "调研中国大陆宠物烘干箱市场"})

    assert result["price_report"]["platform_count"] >= 0
    assert result["market_analysis"]["revenue_model_text"]
    assert "warnings" in result["price_report"]
    assert "source_breakdown" in result["price_report"]
    assert any(stage["workflow_name"] == "price_research" for stage in result["stages"])
    assert any(stage["workflow_name"] == "market_analysis" for stage in result["stages"])


def test_run_research_workflow_preserves_exact_user_product_list() -> None:
    result = run_research_workflow("iPhone 16, 华为 Mate 70, 小米 15")

    assert [item["product_name"] for item in result.products] == [
        "iPhone 16",
        "华为 Mate 70",
        "小米 15",
    ]
    assert result.price_report["sample_size"] >= 0


def test_run_research_workflow_records_fallback_stage_when_model_degrades(monkeypatch: pytest.MonkeyPatch) -> None:
    def fallback_json(self, prompt: str, fallback: dict[str, object]) -> LLMResult:
        return LLMResult(
            value=fallback,
            status="fallback",
            message="模型调用失败，已降级到 fallback 数据",
        )

    def fallback_text(self, prompt: str, fallback: str) -> LLMResult:
        return LLMResult(
            value=fallback,
            status="fallback",
            message="模型调用失败，已降级到 fallback 文本",
        )

    monkeypatch.setattr("app.services.llm_client.LLMClient.generate_json", fallback_json)
    monkeypatch.setattr("app.services.llm_client.LLMClient.generate_structured_text", fallback_text)

    result = run_research_workflow("调研中国大陆宠物烘干箱市场")

    fallback_stages = [stage for stage in result.stages if stage["status"] == "fallback"]
    assert fallback_stages
    assert any("已降级到 fallback" in (stage["message"] or "") for stage in fallback_stages)


def test_run_research_workflow_records_error_stage_when_model_request_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def error_json(self, prompt: str, fallback: dict[str, object]) -> LLMResult:
        return LLMResult(
            value=fallback,
            status="error",
            message="模型请求失败：upstream timeout",
        )

    def error_text(self, prompt: str, fallback: str) -> LLMResult:
        return LLMResult(
            value=fallback,
            status="error",
            message="模型请求失败：upstream timeout",
        )

    monkeypatch.setattr("app.services.llm_client.LLMClient.generate_json", error_json)
    monkeypatch.setattr("app.services.llm_client.LLMClient.generate_structured_text", error_text)

    result = run_research_workflow("调研中国大陆宠物烘干箱市场")

    error_stages = [stage for stage in result.stages if stage["status"] == "error"]
    assert error_stages
    assert any("模型请求失败" in (stage["message"] or "") for stage in error_stages)
    assert result.summary


def test_llm_review_price_rows_limits_preview_rows_to_five(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_prompt = {}
    rows = [
        {
            "product_name": f"产品{i}",
            "platform_name": "平台A",
            "platform_domain": "example.com",
            "product_url": f"https://example.com/{i}",
            "raw_title": f"标题{i}",
            "spec_text": "默认规格",
            "currency": "CNY",
            "raw_price": 100 + i,
            "normalized_price": 100 + i,
            "price_unit": "件",
            "confidence_score": 0.9,
            "is_outlier": False,
            "attempt_count": 1,
            "source": "html_fetch",
        }
        for i in range(8)
    ]

    def stub_generate_json(self, prompt: str, fallback: dict[str, object]) -> LLMResult:
        captured_prompt["prompt"] = prompt
        return LLMResult(value=fallback, status="fallback", message="timeout")

    monkeypatch.setattr("app.services.llm_client.LLMClient.generate_json", stub_generate_json)

    reviewed_rows, _ = _llm_review_price_rows("调研宠物市场", rows)

    assert reviewed_rows == rows
    assert "产品0" in captured_prompt["prompt"]
    assert "产品4" in captured_prompt["prompt"]
    assert "产品5" not in captured_prompt["prompt"]


def test_discover_platforms_uses_llm_selected_final_platforms(monkeypatch: pytest.MonkeyPatch) -> None:
    def stub_search_web(self, prompt: str, fallback: dict[str, object]) -> LLMResult:
        if "宠物烘干箱 标准款" in prompt:
            platforms = [
                {
                    "platform_name": f"A平台{i}",
                    "platform_domain": f"a-platform{i}.com",
                    "platform_url": f"https://a-platform{i}.com/item/{i}",
                    "platform_summary": f"A简介{i}",
                    "platform_type": "marketplace",
                    "priority": i,
                    "reason": f"A原因{i}",
                }
                for i in range(1, 11)
            ]
        else:
            platforms = [
                {
                    "platform_name": f"B平台{i}",
                    "platform_domain": f"b-platform{i}.com",
                    "platform_url": f"https://b-platform{i}.com/item/{i}",
                    "platform_summary": f"B简介{i}",
                    "platform_type": "marketplace",
                    "priority": i,
                    "reason": f"B原因{i}",
                }
                for i in range(1, 11)
            ]
        return LLMResult(value={"platforms": platforms}, status="success")

    monkeypatch.setattr("app.services.llm_client.LLMClient.search_web", stub_search_web)

    state = {
        "prompt": "调研宠物烘干箱市场",
        "products": [
            {"product_name": "宠物烘干箱 标准款", "source_type": "category_inferred", "input_order": 1},
            {"product_name": "宠物烘干箱 Pro", "source_type": "category_inferred", "input_order": 2},
        ],
    }

    result = discover_platforms(state)

    assert len(result["product_platforms"]) == 2
    assert len(result["product_platforms"][0]["platforms"]) == 10
    assert len(result["product_platforms"][1]["platforms"]) == 10
    assert len(result["platforms"]) == 20
    assert result["product_platforms"][0]["platforms"][0]["platform_url"] == "https://a-platform1.com/item/1"
    assert result["product_platforms"][1]["platforms"][0]["platform_summary"] == "B简介1"


def test_discover_platforms_retries_web_search_until_ten_real_platforms(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def stub_search_web(self, prompt: str, fallback: dict[str, object]) -> LLMResult:
        calls.append(prompt)
        if len(calls) == 1:
            return LLMResult(
                value={
                    "platforms": [
                        {
                            "platform_name": f"平台{i}",
                            "platform_domain": f"platform{i}.com",
                            "platform_url": f"https://platform{i}.com/item/{i}",
                            "platform_summary": f"简介{i}",
                            "platform_type": "marketplace",
                            "priority": i,
                            "reason": f"原因{i}",
                        }
                        for i in range(1, 7)
                    ]
                },
                status="success",
            )
        return LLMResult(
            value={
                "platforms": [
                    {
                        "platform_name": f"平台{i}",
                        "platform_domain": f"platform{i}.com",
                        "platform_url": f"https://platform{i}.com/item/{i}",
                        "platform_summary": f"简介{i}",
                        "platform_type": "marketplace",
                        "priority": i,
                        "reason": f"原因{i}",
                    }
                    for i in range(7, 13)
                ]
            },
            status="success",
        )

    monkeypatch.setattr("app.services.llm_client.LLMClient.search_web", stub_search_web)

    result = discover_platforms(
        {
            "prompt": "调研宠物烘干箱市场",
            "products": [{"product_name": "宠物烘干箱", "source_type": "category_inferred", "input_order": 1}],
        }
    )

    assert len(calls) == 2
    assert len(result["product_platforms"]) == 1
    assert len(result["product_platforms"][0]["platforms"]) == 10
    assert result["product_platforms"][0]["platforms"][-1]["platform_domain"] == "platform10.com"
    assert "已排除平台域名" in calls[1]


def test_discover_platforms_returns_existing_real_results_after_three_rounds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def stub_search_web(self, prompt: str, fallback: dict[str, object]) -> LLMResult:
        calls.append(prompt)
        return LLMResult(
            value={
                "platforms": [
                    {
                        "platform_name": "京东",
                        "platform_domain": "jd.com",
                        "platform_url": "https://item.jd.com/1001.html",
                        "platform_summary": "综合电商平台",
                        "platform_type": "marketplace",
                        "priority": 1,
                        "reason": "有效",
                    },
                    {
                        "platform_name": "无效站",
                        "platform_domain": "not a domain",
                        "platform_url": "bad-url",
                        "platform_summary": "无效",
                        "platform_type": "marketplace",
                        "priority": 2,
                        "reason": "无效",
                    },
                ]
            },
            status="success",
        )

    monkeypatch.setattr("app.services.llm_client.LLMClient.search_web", stub_search_web)

    result = discover_platforms(
        {
            "prompt": "调研宠物烘干箱市场",
            "products": [{"product_name": "宠物烘干箱", "source_type": "category_inferred", "input_order": 1}],
        }
    )

    assert len(calls) == 3
    assert len(result["product_platforms"]) == 1
    assert len(result["product_platforms"][0]["platforms"]) == 1
    assert result["product_platforms"][0]["platforms"][0]["platform_domain"] == "jd.com"
    assert result["product_platforms"][0]["platforms"][0]["source"] == "llm_web_search"


def test_crawl_prices_parallel_uses_product_specific_platform_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def stub_crawl_product_prices(self, product, platforms, max_rounds=3):
        captured["product"] = product
        captured["platforms"] = platforms
        return [
            {
                "product_name": str(product["product_name"]),
                "platform_name": str(platforms[0]["platform_name"]),
                "platform_domain": str(platforms[0]["platform_domain"]),
                "product_url": str(platforms[0]["platform_url"]),
                "raw_title": str(product["product_name"]),
                "spec_text": "默认规格",
                "currency": "CNY",
                "raw_price": 100,
                "normalized_price": 100,
                "price_unit": "件",
                "confidence_score": 0.9,
                "is_outlier": False,
                "attempt_count": 1,
                "source": "html_fetch",
            }
        ]

    class FakeExecutor:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def submit(self, fn, product, platforms, max_rounds):
            future: Future = Future()
            future.set_result(fn(product, platforms, max_rounds))
            return future

    monkeypatch.setattr("app.services.crawl_service.PriceCrawlerService.crawl_product_prices", stub_crawl_product_prices)
    monkeypatch.setattr("app.workflows.research_workflow.ThreadPoolExecutor", FakeExecutor)
    monkeypatch.setattr(
        "app.workflows.research_workflow._llm_review_price_rows",
        lambda prompt, rows: (rows, []),
    )

    result = crawl_prices_parallel(
        {
            "prompt": "调研测试市场",
            "products": [
                {"product_name": "产品A", "source_type": "user_specified", "input_order": 1},
                {"product_name": "产品B", "source_type": "user_specified", "input_order": 2},
            ],
            "platforms": [],
            "product_platforms": [
                {
                    "product_name": "产品A",
                    "platforms": [{"platform_name": "平台A1", "platform_domain": "a1.com", "platform_url": "https://a1.com/item/1"}],
                },
                {
                    "product_name": "产品B",
                    "platforms": [{"platform_name": "平台B1", "platform_domain": "b1.com", "platform_url": "https://b1.com/item/1"}],
                },
            ],
        }
    )

    assert captured["product"]["product_name"] in {"产品A", "产品B"}
    assert captured["platforms"][0]["platform_domain"] in {"a1.com", "b1.com"}
    assert result["price_records"][0]["platform_domain"] == "a1.com"


def test_crawl_prices_parallel_runs_one_parallel_job_per_product(monkeypatch: pytest.MonkeyPatch) -> None:
    submitted: list[tuple[str, list[dict[str, object]]]] = []

    class FakeExecutor:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def submit(self, fn, product, platforms, max_rounds):
            submitted.append((str(product["product_name"]), platforms))
            future: Future = Future()
            future.set_result(
                [
                    {
                        "product_name": str(product["product_name"]),
                        "platform_name": str(platforms[0]["platform_name"]),
                        "platform_domain": str(platforms[0]["platform_domain"]),
                        "product_url": str(platforms[0]["platform_url"]),
                        "raw_title": str(product["product_name"]),
                        "spec_text": "默认规格",
                        "currency": "CNY",
                        "raw_price": None,
                        "normalized_price": None,
                        "price_unit": None,
                        "confidence_score": 0.0,
                        "is_outlier": False,
                        "attempt_count": 1,
                        "source": "markdown_llm_unpriced",
                        "notes": "抓到网页但未识别出价格",
                    }
                ]
            )
            return future

    monkeypatch.setattr("app.workflows.research_workflow.ThreadPoolExecutor", FakeExecutor)
    monkeypatch.setattr(
        "app.workflows.research_workflow._llm_review_price_rows",
        lambda prompt, rows: (rows, []),
    )

    result = crawl_prices_parallel(
        {
            "prompt": "调研测试市场",
            "products": [
                {"product_name": "产品A", "source_type": "user_specified", "input_order": 1},
                {"product_name": "产品B", "source_type": "user_specified", "input_order": 2},
            ],
            "platforms": [],
            "product_platforms": [
                {
                    "product_name": "产品A",
                    "platforms": [{"platform_name": "平台A1", "platform_domain": "a1.com", "platform_url": "https://a1.com/item/1"}],
                },
                {
                    "product_name": "产品B",
                    "platforms": [{"platform_name": "平台B1", "platform_domain": "b1.com", "platform_url": "https://b1.com/item/1"}],
                },
            ],
        }
    )

    assert len(submitted) == 2
    assert submitted[0][0] == "产品A"
    assert submitted[1][0] == "产品B"
    assert submitted[0][1][0]["platform_domain"] == "a1.com"
    assert submitted[1][1][0]["platform_domain"] == "b1.com"
    assert len(result["price_records"]) == 2


def test_discover_platforms_writes_workflow_logs(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr("app.core.logging.get_settings", lambda: Settings(app_log_dir=str(tmp_path)))

    def stub_search_web(self, prompt: str, fallback: dict[str, object]) -> LLMResult:
        return LLMResult(
            value={
                "platforms": [
                    {
                        "platform_name": "京东",
                        "platform_domain": "jd.com",
                        "platform_url": "https://item.jd.com/1001.html",
                        "platform_summary": "综合电商平台",
                        "platform_type": "marketplace",
                        "priority": 1,
                        "reason": "有效",
                    }
                ]
            },
            status="success",
        )

    monkeypatch.setattr("app.services.llm_client.LLMClient.search_web", stub_search_web)

    state = {
        "prompt": "调研宠物烘干箱市场",
        "products": [{"product_name": "宠物烘干箱", "source_type": "category_inferred", "input_order": 1}],
    }

    discover_platforms(state)

    content = (tmp_path / "app.log").read_text(encoding="utf-8")
    assert "workflow_node_start node=discover_platforms" in content
    assert "workflow_node_end node=discover_platforms" in content


def test_discover_platforms_uses_web_search_evidence_from_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    def stub_search_web(self, prompt: str, fallback: dict[str, object]) -> LLMResult:
        return LLMResult(
            value={
                "platforms": [
                    {
                        "platform_name": "京东",
                        "platform_domain": "jd.com",
                        "platform_url": "https://item.jd.com/1001.html",
                        "platform_summary": "综合电商平台",
                        "platform_type": "marketplace",
                        "priority": 1,
                        "reason": "搜索命中商品页",
                        "search_evidence": [
                            {
                                "query": "宠物烘干箱 京东",
                                "title": "京东宠物烘干箱",
                                "url": "https://www.jd.com/item/1",
                                "snippet": "商品页",
                            }
                        ],
                    }
                ]
            },
            status="success",
        )

    monkeypatch.setattr("app.services.llm_client.LLMClient.search_web", stub_search_web)

    state = {
        "prompt": "调研宠物烘干箱市场",
        "products": [{"product_name": "宠物烘干箱", "source_type": "category_inferred", "input_order": 1}],
    }

    result = discover_platforms(state)

    assert result["platforms"][0]["source"] == "llm_web_search"
    assert result["platforms"][0]["search_evidence"][0]["url"] == "https://www.jd.com/item/1"


def test_crawl_prices_parallel_prefers_product_target_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def stub_crawl_prices(self, products, platforms, max_rounds=3, product_platforms=None):
        captured["platforms"] = platforms
        captured["product_platforms"] = product_platforms
        return [
            {
                "product_name": "宠物烘干箱",
                "platform_name": "京东",
                "platform_domain": "jd.com",
                "product_url": "https://item.jd.com/1001.html",
                "raw_title": "京东宠物烘干箱",
                "spec_text": "默认规格",
                "currency": "CNY",
                "raw_price": 999.0,
                "normalized_price": 999.0,
                "price_unit": "件",
                "confidence_score": 0.92,
                "is_outlier": False,
                "attempt_count": 1,
                "source": "html_fetch",
            }
        ]

    monkeypatch.setattr("app.services.crawl_service.PriceCrawlerService.crawl_prices", stub_crawl_prices)
    monkeypatch.setattr(
        "app.workflows.research_workflow._llm_review_price_rows",
        lambda prompt, rows: (rows, []),
    )

    state = {
        "prompt": "调研宠物烘干箱市场",
        "products": [{"product_name": "宠物烘干箱", "source_type": "category_inferred", "input_order": 1}],
        "platforms": [
            {
                "platform_name": "京东",
                "platform_domain": "jd.com",
                "platform_url": "https://item.jd.com/1001.html",
                "platform_summary": "综合电商平台",
                "discover_round": 1,
                "platform_type": "marketplace",
                "source": "llm_web_search",
            }
        ],
    }

    result = crawl_prices_parallel(state)

    assert captured["platforms"] == state["platforms"]
    assert captured["product_platforms"] is None
    assert result["price_records"][0]["product_url"] == "https://item.jd.com/1001.html"
