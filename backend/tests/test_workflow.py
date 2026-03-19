import pytest
from concurrent.futures import Future

from app.core.config import Settings
from app.services.kimi_client import LLMResult
from app.workflows.research_workflow import (
    analyze_prices,
    build_from_zero_plan,
    crawl_prices_parallel,
    discover_platforms,
    get_research_graph,
    normalize_prices,
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


def test_discover_platforms_runs_one_parallel_job_per_product(monkeypatch: pytest.MonkeyPatch) -> None:
    submitted: list[str] = []

    class FakeExecutor:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def submit(self, fn, prompt, product, max_platforms):
            submitted.append(str(product["product_name"]))
            future: Future = Future()
            future.set_result(
                (
                    [
                        {
                            "platform_name": f"{product['product_name']}平台",
                            "platform_domain": f"{product['input_order']}.example.com",
                            "platform_url": f"https://{product['input_order']}.example.com/item/1",
                            "platform_summary": f"{product['product_name']}简介",
                            "platform_type": "marketplace",
                            "priority": 1,
                            "reason": "有效",
                            "source": "llm_web_search",
                        }
                    ],
                    [],
                    {"candidate_count": 1, "invalid_count": 0, "selected_count": 1, "final_count": 1},
                )
            )
            return future

    monkeypatch.setattr("app.workflows.research_workflow.ThreadPoolExecutor", FakeExecutor)
    monkeypatch.setattr(
        "app.workflows.research_workflow._llm_select_final_platforms_for_product",
        lambda prompt, product, max_platforms: (
            [
                {
                    "platform_name": f"{product['product_name']}平台",
                    "platform_domain": f"{product['input_order']}.example.com",
                    "platform_url": f"https://{product['input_order']}.example.com/item/1",
                    "platform_summary": f"{product['product_name']}简介",
                    "platform_type": "marketplace",
                    "priority": 1,
                    "reason": "有效",
                    "source": "llm_web_search",
                }
            ],
            [],
            {"candidate_count": 1, "invalid_count": 0, "selected_count": 1, "final_count": 1},
        ),
    )

    result = discover_platforms(
        {
            "prompt": "调研宠物烘干箱市场",
            "products": [
                {"product_name": "产品A", "source_type": "user_specified", "input_order": 1},
                {"product_name": "产品B", "source_type": "user_specified", "input_order": 2},
            ],
        }
    )

    assert submitted == ["产品A", "产品B"]
    assert [item["product_name"] for item in result["product_platforms"]] == ["产品A", "产品B"]
    assert result["product_platforms"][0]["platforms"][0]["platform_domain"] == "1.example.com"
    assert result["product_platforms"][1]["platforms"][0]["platform_domain"] == "2.example.com"


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


def test_discover_platforms_continues_later_rounds_after_single_round_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def stub_search_web(self, prompt: str, fallback: dict[str, object]) -> LLMResult:
        nonlocal calls
        calls += 1
        if calls == 1:
            return LLMResult(
                value={"platforms": []},
                status="fallback",
                message="火山方舟 web search 返回格式异常，本轮平台搜索结果已按空结果处理",
            )
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

    result = discover_platforms(
        {
            "prompt": "调研宠物烘干箱市场",
            "products": [{"product_name": "宠物烘干箱", "source_type": "category_inferred", "input_order": 1}],
        }
    )

    assert calls == 3
    assert len(result["product_platforms"]) == 1
    assert len(result["product_platforms"][0]["platforms"]) == 1
    assert result["product_platforms"][0]["platforms"][0]["platform_domain"] == "jd.com"
    assert any(stage["status"] == "fallback" for stage in result["stages"])


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
    assert not any(stage["stage_name"] == "llm_review_price_rows" for stage in result["stages"])


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
    assert result["stages"][-1]["status"] == "failed"
    assert not any(stage["stage_name"] == "llm_review_price_rows" for stage in result["stages"])


def test_crawl_prices_parallel_marks_failed_when_no_valid_prices(monkeypatch: pytest.MonkeyPatch) -> None:
    def stub_crawl_prices(self, products, platforms, max_rounds=3, product_platforms=None):
        return [
            {
                "product_name": "产品A",
                "platform_name": "平台A1",
                "platform_domain": "a1.com",
                "product_url": "https://a1.com/item/1",
                "raw_title": "产品A",
                "spec_text": "",
                "currency": "CNY",
                "raw_price": None,
                "normalized_price": None,
                "price_unit": None,
                "confidence_score": 0.0,
                "is_outlier": False,
                "attempt_count": 1,
                "source": "playwright_fetch_failed",
                "notes": "browser timeout",
            }
        ]

    monkeypatch.setattr("app.services.crawl_service.PriceCrawlerService.crawl_prices", stub_crawl_prices)
    result = crawl_prices_parallel(
        {
            "prompt": "调研测试市场",
            "products": [{"product_name": "产品A", "source_type": "user_specified", "input_order": 1}],
            "platforms": [{"platform_name": "平台A1", "platform_domain": "a1.com", "platform_url": "https://a1.com/item/1"}],
        }
    )

    assert result["stages"][-1]["stage_name"] == "crawl_prices_parallel"
    assert result["stages"][-1]["status"] == "failed"
    assert "未识别出任何有效价格" in result["stages"][-1]["message"]
    assert not any(stage["stage_name"] == "llm_review_price_rows" for stage in result["stages"])


def test_crawl_prices_parallel_marks_completed_when_some_valid_prices_exist(monkeypatch: pytest.MonkeyPatch) -> None:
    def stub_crawl_prices(self, products, platforms, max_rounds=3, product_platforms=None):
        return [
            {
                "product_name": "产品A",
                "platform_name": "平台A1",
                "platform_domain": "a1.com",
                "product_url": "https://a1.com/item/1",
                "raw_title": "产品A",
                "spec_text": "",
                "currency": "CNY",
                "raw_price": 99,
                "normalized_price": 99,
                "price_unit": "件",
                "confidence_score": 0.9,
                "is_outlier": False,
                "attempt_count": 1,
                "source": "markdown_llm_price",
            },
            {
                "product_name": "产品A",
                "platform_name": "平台A2",
                "platform_domain": "a2.com",
                "product_url": "https://a2.com/item/2",
                "raw_title": "产品A",
                "spec_text": "",
                "currency": "CNY",
                "raw_price": None,
                "normalized_price": None,
                "price_unit": None,
                "confidence_score": 0.0,
                "is_outlier": False,
                "attempt_count": 1,
                "source": "playwright_fetch_failed",
                "notes": "browser timeout",
            },
        ]

    monkeypatch.setattr("app.services.crawl_service.PriceCrawlerService.crawl_prices", stub_crawl_prices)
    result = crawl_prices_parallel(
        {
            "prompt": "调研测试市场",
            "products": [{"product_name": "产品A", "source_type": "user_specified", "input_order": 1}],
            "platforms": [{"platform_name": "平台A1", "platform_domain": "a1.com", "platform_url": "https://a1.com/item/1"}],
        }
    )

    assert result["stages"][-1]["status"] == "completed"
    assert "其中 1 条识别出有效价格" in result["stages"][-1]["message"]
    assert not any(stage["stage_name"] == "llm_review_price_rows" for stage in result["stages"])


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
    assert not any(stage["stage_name"] == "llm_review_price_rows" for stage in result["stages"])


def test_normalize_prices_reports_filter_and_dedup_stats() -> None:
    result = normalize_prices(
        {
            "prompt": "调研电动牙刷市场",
            "price_records": [
                {
                    "product_name": "电动牙刷",
                    "platform_name": "京东",
                    "platform_domain": "jd.com",
                    "product_url": "https://jd.com/item/1",
                    "raw_title": "电动牙刷A",
                    "spec_text": "默认规格",
                    "currency": "cny",
                    "raw_price": "199",
                    "normalized_price": None,
                    "price_unit": "个",
                    "confidence_score": "0.70",
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
                    "raw_price": "199",
                    "normalized_price": "199",
                    "price_unit": "件",
                    "confidence_score": "0.95",
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
                    "attempt_count": 1,
                    "source": "markdown_llm_unpriced",
                },
            ],
        }
    )

    assert len(result["price_records"]) == 1
    assert result["price_records"][0]["price_unit"] == "件"
    assert result["stages"][-1]["stage_name"] == "normalize_prices"
    assert "删除 1 条空价格记录" in result["stages"][-1]["message"]
    assert "去重 1 条" in result["stages"][-1]["message"]
    assert result["stages"][-1]["detail_json"]["stats"]["final_count"] == 1


def test_normalize_prices_sends_all_rows_with_minimal_fields_to_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def stub_generate_json(self, prompt: str, fallback: dict[str, object]) -> LLMResult:
        captured["prompt"] = prompt
        captured["fallback"] = fallback
        return LLMResult(
            value={
                "rows": [
                    {
                        "row_id": 0,
                        "product_name": "RTX 4090",
                        "platform_name": "平台A",
                        "platform_domain": "a.example.com",
                        "product_url": "https://a.example.com/item/1",
                        "raw_title": "4090 A",
                        "spec_text": "单卡",
                        "currency": "CNY",
                        "raw_price": 2.5,
                        "normalized_price": 2.5,
                        "price_unit": "小时",
                    },
                    {
                        "row_id": 1,
                        "product_name": "RTX 5090",
                        "platform_name": "平台B",
                        "platform_domain": "b.example.com",
                        "product_url": "https://b.example.com/item/2",
                        "raw_title": "5090 B",
                        "spec_text": "包月",
                        "currency": "CNY",
                        "raw_price": 5000,
                        "normalized_price": 5000,
                        "price_unit": "件",
                    },
                ]
            },
            status="success",
        )

    monkeypatch.setattr("app.services.llm_client.LLMClient.generate_json", stub_generate_json)

    result = normalize_prices(
        {
            "prompt": "调研GPU租赁市场",
            "price_records": [
                {
                    "product_name": "4090",
                    "platform_name": "平台A",
                    "platform_domain": "a.example.com",
                    "product_url": "https://a.example.com/item/1",
                    "raw_title": "4090 A",
                    "spec_text": "",
                    "currency": "cny",
                    "raw_price": 2.5,
                    "normalized_price": 2.5,
                    "price_unit": None,
                    "confidence_score": 0.8,
                    "attempt_count": 1,
                    "source": "markdown_llm_price",
                    "notes": "抓取成功",
                    "markdown_excerpt": "很长的网页摘录A",
                },
                {
                    "product_name": "5090",
                    "platform_name": "平台B",
                    "platform_domain": "b.example.com",
                    "product_url": "https://b.example.com/item/2",
                    "raw_title": "5090 B",
                    "spec_text": "",
                    "currency": "cny",
                    "raw_price": 5000,
                    "normalized_price": 5000,
                    "price_unit": None,
                    "confidence_score": 0.9,
                    "attempt_count": 1,
                    "source": "markdown_llm_price",
                    "notes": "抓取成功",
                    "markdown_excerpt": "很长的网页摘录B",
                },
            ],
        }
    )

    prompt = str(captured["prompt"])
    fallback = captured["fallback"]
    assert "row_id" in prompt
    assert "很长的网页摘录A" not in prompt
    assert "很长的网页摘录B" not in prompt
    assert "抓取成功" not in prompt
    assert isinstance(fallback, dict)
    assert len(fallback["rows"]) == 2
    assert result["price_records"][0]["product_name"] == "RTX 4090"
    assert result["price_records"][0]["price_unit"] == "小时"
    assert result["price_records"][0]["markdown_excerpt"] == "很长的网页摘录A"
    assert result["price_records"][1]["product_name"] == "RTX 5090"


def test_analyze_prices_ignores_legacy_fallback_seed_warnings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.llm_client.LLMClient.generate_json",
        lambda self, prompt, fallback: LLMResult(value=fallback, status="success"),
    )

    result = analyze_prices(
        {
            "prompt": "调研电动牙刷市场",
            "platforms": [
                {
                    "platform_name": "旧平台",
                    "platform_domain": "old.example.com",
                    "source": "fallback_seed",
                }
            ],
            "price_records": [
                {
                    "product_name": "电动牙刷",
                    "platform_name": "旧平台",
                    "platform_domain": "old.example.com",
                    "product_url": "https://old.example.com/item/1",
                    "normalized_price": 199.0,
                    "attempt_count": 1,
                    "source": "default_seed",
                }
            ],
        }
    )

    warnings = result["price_report"]["warnings"]
    assert "部分平台使用 fallback 数据" not in warnings
    assert "部分价格来自默认种子数据" not in warnings


def test_build_from_zero_plan_does_not_emit_legacy_fallback_data_quality(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.llm_client.LLMClient.generate_structured_text",
        lambda self, prompt, fallback: LLMResult(value="构建方案", status="success"),
    )

    result = build_from_zero_plan(
        {
            "topic": "调研电动牙刷市场",
            "platforms": [
                {
                    "platform_name": "旧平台",
                    "platform_domain": "old.example.com",
                    "source": "fallback_seed",
                }
            ],
            "market_analysis": {
                "summary_json": {},
            },
        }
    )

    assert result["market_analysis"]["summary_json"] == {}


def test_analyze_prices_builds_chart_datasets_and_preserves_row_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.llm_client.LLMClient.generate_json",
        lambda self, prompt, fallback: LLMResult(value=fallback, status="success"),
    )

    result = analyze_prices(
        {
            "prompt": "调研电动牙刷市场",
            "platforms": [
                {"platform_name": "京东", "platform_domain": "jd.com", "source": "llm_web_search"},
                {"platform_name": "淘宝", "platform_domain": "taobao.com", "source": "llm_web_search"},
            ],
            "price_records": [
                {
                    "product_name": "电动牙刷 标准款",
                    "platform_name": "京东",
                    "platform_domain": "jd.com",
                    "product_url": "https://jd.com/item/1",
                    "normalized_price": 199.0,
                    "attempt_count": 1,
                    "source": "markdown_llm_price",
                    "notes": "",
                },
                {
                    "product_name": "电动牙刷 标准款",
                    "platform_name": "淘宝",
                    "platform_domain": "taobao.com",
                    "product_url": "https://taobao.com/item/2",
                    "normalized_price": 189.0,
                    "attempt_count": 1,
                    "source": "markdown_llm_price",
                    "notes": "",
                },
                {
                    "product_name": "电动牙刷 Pro",
                    "platform_name": "京东",
                    "platform_domain": "jd.com",
                    "product_url": "https://jd.com/item/3",
                    "normalized_price": None,
                    "attempt_count": 1,
                    "source": "markdown_llm_unpriced",
                    "notes": "抓到网页但未识别出价格",
                },
            ],
        }
    )

    report = result["price_report"]
    assert {row["product_url"] for row in report["rows"]} == {
        "https://jd.com/item/1",
        "https://taobao.com/item/2",
        "https://jd.com/item/3",
    }
    assert report["sample_size"] == 2
    assert report["row_count"] == 3
    assert report["charts"]["product_platform_prices"]["products"] == ["电动牙刷 Pro", "电动牙刷 标准款"]
    assert report["charts"]["platform_average_prices"][0]["platform_name"] == "京东"
    assert report["charts"]["coverage_matrix"]["cells"][0]["product_name"]
    assert report["charts"]["source_breakdown"][0]["source"] in {"markdown_llm_price", "markdown_llm_unpriced"}
