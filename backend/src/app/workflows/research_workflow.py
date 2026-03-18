from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from operator import add
from statistics import mean
from typing import Annotated, Any, TypedDict
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import re

from langgraph.graph import END, START, StateGraph

from app.core.logging import get_app_logger
from app.services.crawl_service import PriceCrawlerService
from app.services.kimi_client import LLMResult
from app.services.llm_client import LLMClient
from app.services.normalize_service import normalize_price_records


@dataclass
class WorkflowResult:
    products: list[dict[str, Any]]
    platforms: list[dict[str, Any]]
    price_records: list[dict[str, Any]]
    price_report: dict[str, Any]
    market_analysis: dict[str, Any]
    stages: list[dict[str, Any]]
    summary: str


def _llm_stage(
    *,
    workflow_name: str,
    stage_name: str,
    result: LLMResult[Any],
) -> list[dict[str, Any]]:
    if result.status == "success" or not result.message:
        return []
    return [
        {
            "workflow_name": workflow_name,
            "stage_name": stage_name,
            "status": result.status,
            "message": result.message,
            "detail_json": {
                "provider": result.provider,
                "model": result.model,
                "method": result.method,
                "prompt": result.prompt,
                "result": result.value,
                "status": result.status,
                "message": result.message,
            },
            "retry_count": 0,
        }
    ]


def _completed_stage(
    *,
    workflow_name: str,
    stage_name: str,
    message: str,
    detail_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "workflow_name": workflow_name,
        "stage_name": stage_name,
        "status": "completed",
        "message": message,
        "detail_json": detail_json,
        "retry_count": 0,
    }


class ResearchWorkflowState(TypedDict, total=False):
    prompt: str
    topic: str
    intent_type: str
    products: list[dict[str, Any]]
    platforms: list[dict[str, Any]]
    product_platforms: list[dict[str, Any]]
    price_records: list[dict[str, Any]]
    price_report: dict[str, Any]
    market_analysis: dict[str, Any]
    summary: str
    stages: Annotated[list[dict[str, Any]], add]


def _pick_products(prompt: str) -> tuple[list[dict[str, Any]], str]:
    stripped = [item.strip() for item in prompt.replace("、", ",").split(",") if item.strip()]
    if len(stripped) > 1:
        return (
            [
                {"product_name": name, "source_type": "user_specified", "input_order": idx}
                for idx, name in enumerate(stripped, start=1)
            ],
            "specific",
        )

    topic = prompt.strip()
    samples = [
        f"{topic} 标准款",
        f"{topic} Pro",
        f"{topic} Mini",
        f"{topic} 青春版",
        f"{topic} 旗舰版",
    ]
    return (
        [
            {"product_name": name, "source_type": "category_inferred", "input_order": idx}
            for idx, name in enumerate(samples[:5], start=1)
        ],
        "category",
    )


def _llm_select_products(prompt: str) -> tuple[list[dict[str, Any]], str, list[dict[str, Any]]]:
    fallback_products, fallback_intent = _pick_products(prompt)
    client = LLMClient()
    fallback_payload = {
        "intent_type": fallback_intent,
        "products": fallback_products,
    }
    result = client.generate_json(
        f"""
你是市场调研工作流的产品识别节点。
用户输入: {prompt}

任务:
1. 判断用户输入的是“具体产品列表”还是“产品类别”。
2. 如果是具体产品列表，products 必须严格保留用户给出的产品，不增不减。
3. 如果是产品类别，选择最多 5 个最具代表性的具体产品。

返回 JSON:
{{
  "intent_type": "specific" | "category",
  "products": [
    {{
      "product_name": "string",
      "source_type": "user_specified" | "category_inferred",
      "input_order": 1
    }}
  ]
}}
""",
        fallback=fallback_payload,
    )
    payload = result.value
    products = payload.get("products", fallback_products) or fallback_products
    intent_type = str(payload.get("intent_type", fallback_intent))
    return products, intent_type, _llm_stage(
        workflow_name="price_research",
        stage_name="llm_select_products",
        result=result,
    )


def _llm_rank_platforms(
    prompt: str,
    products: list[dict[str, Any]],
    platforms: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    client = LLMClient()
    fallback_payload = {"platform_domains": [platform["platform_domain"] for platform in platforms[:5]]}
    result = client.generate_json(
        f"""
你是市场调研工作流的平台筛选节点。
用户输入: {prompt}
候选产品: {products}
候选平台: {platforms}

任务:
从候选平台中选出最适合这些产品调研的最多 5 个平台。

返回 JSON:
{{
  "platform_domains": ["jd.com", "tmall.com"]
}}
""",
        fallback=fallback_payload,
    )
    payload = result.value
    selected_domains = payload.get("platform_domains", fallback_payload["platform_domains"])
    ranked = [platform for platform in platforms if platform["platform_domain"] in selected_domains]
    return (
        ranked[:5] or platforms[:5],
        _llm_stage(
            workflow_name="price_research",
            stage_name="llm_rank_platforms",
            result=result,
        ),
    )


def _is_valid_platform_domain(domain: str) -> bool:
    return bool(re.fullmatch(r"[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+", domain))


def _is_valid_platform_url(url: str) -> bool:
    return url.startswith(("http://", "https://"))


def _build_platform_search_prompt(
    prompt: str,
    product: dict[str, Any],
    max_platforms: int,
    excluded_domains: set[str],
) -> str:
    excluded_text = f"已排除平台域名: {sorted(excluded_domains)}" if excluded_domains else "已排除平台域名: []"
    return f"""
你是市场调研工作流的平台发现节点。
用户输入: {prompt}
目标产品: {product}
{excluded_text}

任务:
1. 使用实时 web search 联网搜索与这些产品相关、能够直接显示商品价格的页面。
2. 返回至少 {max_platforms} 个平台候选；如果本轮找不到那么多，就尽量返回更多真实结果。
3. platform_url 必须是该平台上能看到商品价格的页面 URL，不要返回平台主页、资讯页、论坛页或搜索引擎链接。
4. platform_domain 必须是平台主域名，不要返回搜索引擎域名。
5. 为每个平台附带 1 到 2 句话的简介 platform_summary。
6. 不要返回已排除的平台域名。

返回 JSON:
{{
  "platforms": [
    {{
      "platform_name": "京东",
      "platform_domain": "jd.com",
      "platform_url": "https://item.jd.com/1001.html",
      "platform_summary": "中国大陆主流综合电商平台，商品页通常直接展示价格。",
      "platform_type": "marketplace",
      "priority": 1,
      "reason": "适合该类商品调研",
      "search_evidence": [
        {{
          "query": "宠物烘干箱 site:jd.com",
          "title": "京东宠物烘干箱商品页",
          "url": "https://item.jd.com/1001.html",
          "snippet": "宠物烘干箱商品详情"
        }}
      ]
    }}
  ]
}}
"""


def _llm_select_final_platforms_for_product(
    prompt: str,
    product: dict[str, Any],
    max_platforms: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    client = LLMClient()
    excluded_domains: set[str] = set()
    deduped: dict[str, dict[str, Any]] = {}
    invalid_count = 0
    total_candidates = 0
    stage_updates: list[dict[str, Any]] = []

    for round_number in range(1, 4):
        result = client.search_web(
            _build_platform_search_prompt(prompt, product, max_platforms, excluded_domains),
            fallback={"platforms": []},
        )
        stage_updates.extend(
            _llm_stage(
                workflow_name="price_research",
                stage_name="llm_select_final_platforms",
                result=result,
            )
        )
        payload = result.value
        candidates = payload.get("platforms", []) or []
        total_candidates += len(candidates)

        for index, candidate in enumerate(candidates, start=1):
            domain = str(candidate.get("platform_domain", "")).strip().lower()
            platform_url = str(candidate.get("platform_url", "")).strip()
            if not _is_valid_platform_domain(domain) or not _is_valid_platform_url(platform_url):
                invalid_count += 1
                continue
            if domain in deduped:
                invalid_count += 1
                continue

            deduped[domain] = {
                "platform_name": str(candidate.get("platform_name", domain)),
                "platform_domain": domain,
                "platform_url": platform_url,
                "platform_summary": str(candidate.get("platform_summary", "")),
                "discover_round": round_number,
                "platform_type": str(candidate.get("platform_type", "marketplace")),
                "priority": int(candidate.get("priority", len(deduped) + index)),
                "reason": str(candidate.get("reason", "")),
                "search_evidence": list(candidate.get("search_evidence", [])),
                "source": "llm_web_search",
            }
            excluded_domains.add(domain)
            if len(deduped) >= max_platforms:
                break

        if len(deduped) >= max_platforms or result.status != "success":
            break

    metrics = {
        "candidate_count": total_candidates,
        "invalid_count": invalid_count,
        "selected_count": len(deduped),
        "final_count": len(deduped),
    }
    return list(deduped.values())[:max_platforms], stage_updates, metrics


def _llm_review_price_rows(prompt: str, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    client = LLMClient()
    preview_rows = rows[: min(5, len(rows))]
    fallback_payload = {"rows": preview_rows}
    result = client.generate_json(
        f"""
你是市场调研工作流的价格抓取校验节点。
用户输入: {prompt}
价格候选数据: {preview_rows}

任务:
校验这些价格记录是否合理，必要时修正 title/spec/price_unit 字段。
如果无法判断，保留原值。

返回 JSON:
{{
  "rows": [
    {{
      "product_name": "string",
      "platform_name": "string",
      "platform_domain": "string",
      "product_url": "string",
      "raw_title": "string",
      "spec_text": "string",
      "currency": "CNY",
      "raw_price": 123.45,
      "normalized_price": 123.45,
      "price_unit": "件",
      "confidence_score": 0.9,
      "is_outlier": false,
      "attempt_count": 1,
      "source": "html_fetch"
    }}
  ]
}}
""",
        fallback=fallback_payload,
    )
    payload = result.value
    reviewed_rows = payload.get("rows", preview_rows)
    if len(rows) > len(preview_rows):
        reviewed_rows = reviewed_rows + rows[len(preview_rows) :]
    return reviewed_rows, _llm_stage(
        workflow_name="price_research",
        stage_name="llm_review_price_rows",
        result=result,
    )


def _llm_normalize_rows(prompt: str, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    client = LLMClient()
    preview_rows = rows[: min(10, len(rows))]
    fallback_payload = {"rows": preview_rows}
    result = client.generate_json(
        f"""
你是市场调研工作流的标准化节点。
用户输入: {prompt}
待标准化数据: {preview_rows}

任务:
统一产品名称、规格文案和币种字段，保留价格数值不变。

返回 JSON:
{{
  "rows": [
    {{
      "product_name": "string",
      "platform_name": "string",
      "platform_domain": "string",
      "product_url": "string",
      "raw_title": "string",
      "spec_text": "string",
      "currency": "CNY",
      "raw_price": 123.45,
      "normalized_price": 123.45,
      "price_unit": "件",
      "confidence_score": 0.9,
      "is_outlier": false,
      "attempt_count": 1,
      "source": "html_fetch"
    }}
  ]
}}
""",
        fallback=fallback_payload,
    )
    payload = result.value
    normalized_rows = payload.get("rows", preview_rows)
    if len(rows) > len(preview_rows):
        normalized_rows = normalized_rows + rows[len(preview_rows) :]
    return normalized_rows, _llm_stage(
        workflow_name="price_research",
        stage_name="llm_normalize_rows",
        result=result,
    )


def parse_product_intent(state: ResearchWorkflowState) -> ResearchWorkflowState:
    products, intent_type, llm_stages = _llm_select_products(state["prompt"])
    product_names = "、".join(product["product_name"] for product in products)
    return {
        "intent_type": intent_type,
        "products": products,
        "stages": llm_stages + [
            _completed_stage(
                workflow_name="price_research",
                stage_name="parse_product_intent",
                message=f"识别结果：{intent_type}，共识别 {len(products)} 个候选产品",
                detail_json={
                    "prompt": state["prompt"],
                    "intent_type": intent_type,
                    "products": products,
                },
            ),
            _completed_stage(
                workflow_name="price_research",
                stage_name="select_products",
                message=f"已确定调研产品：{product_names}",
                detail_json={
                    "selected_products": products,
                    "product_names": product_names,
                },
            ),
        ],
    }


def discover_platforms(state: ResearchWorkflowState) -> ResearchWorkflowState:
    workflow_logger = get_app_logger("workflow")
    workflow_logger.info(
        "workflow_node_start node=discover_platforms prompt_preview=%r product_count=%s",
        state["prompt"][:120],
        len(state["products"]),
    )
    llm_stages: list[dict[str, Any]] = []
    product_platforms: list[dict[str, Any]] = []
    all_platforms: list[dict[str, Any]] = []
    total_candidate_count = 0
    total_invalid_count = 0

    for product in state["products"]:
        platforms, product_llm_stages, metrics = _llm_select_final_platforms_for_product(
            state["prompt"],
            product,
            max_platforms=10,
        )
        llm_stages.extend(product_llm_stages)
        product_platforms.append(
            {
                "product_name": product["product_name"],
                "platforms": platforms,
                "metrics": metrics,
            }
        )
        all_platforms.extend(platforms)
        total_candidate_count += metrics["candidate_count"]
        total_invalid_count += metrics["invalid_count"]

    platform_names = "、".join(platform["platform_name"] for platform in all_platforms)
    workflow_logger.info(
        "workflow_node_end node=discover_platforms candidate_count=%s invalid_count=%s final_count=%s platform_names=%r",
        total_candidate_count,
        total_invalid_count,
        len(all_platforms),
        platform_names,
    )
    return {
        "platforms": all_platforms,
        "product_platforms": product_platforms,
        "stages": llm_stages + [
            _completed_stage(
                workflow_name="price_research",
                stage_name="discover_platforms",
                message=(
                    f"共为 {len(product_platforms)} 个商品发现 {len(all_platforms)} 个真实平台，"
                    f"累计产出 {total_candidate_count} 个候选平台，"
                    f"过滤 {total_invalid_count} 个无效/重复平台"
                ),
                detail_json={
                    "prompt": state["prompt"],
                    "products": state["products"],
                    "platforms": all_platforms,
                    "product_platforms": product_platforms,
                    "metrics": {
                        "candidate_count": total_candidate_count,
                        "invalid_count": total_invalid_count,
                        "final_count": len(all_platforms),
                    },
                },
            )
        ],
    }


def crawl_prices_parallel(state: ResearchWorkflowState) -> ResearchWorkflowState:
    crawl_service = PriceCrawlerService()
    product_platforms = state.get("product_platforms") or []
    if product_platforms:
        product_lookup = {str(product["product_name"]): product for product in state["products"]}
        raw_price_records: list[dict[str, Any]] = []
        max_workers = max(1, len(product_platforms))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    crawl_service.crawl_product_prices,
                    product_lookup.get(
                        str(mapping["product_name"]),
                        {"product_name": mapping["product_name"], "source_type": "user_specified", "input_order": index + 1},
                    ),
                    list(mapping.get("platforms", [])),
                    3,
                )
                for index, mapping in enumerate(product_platforms)
            ]
            for future in futures:
                raw_price_records.extend(future.result())
    else:
        raw_price_records = crawl_service.crawl_prices(
            products=state["products"],
            platforms=state["platforms"],
            max_rounds=3,
        )
    price_records, llm_stages = _llm_review_price_rows(state["prompt"], raw_price_records)
    source_breakdown = dict(Counter(str(row.get("source", "unknown")) for row in price_records))
    return {
        "price_records": price_records,
        "stages": llm_stages + [
            _completed_stage(
                workflow_name="price_research",
                stage_name="crawl_prices_parallel",
                message=(
                    f"已抓取 {len(price_records)} 条价格记录，"
                    f"覆盖 {len(product_platforms) or len(state['products'])} 个商品任务，"
                    f"来源分布：{source_breakdown}"
                ),
                detail_json={
                    "prompt": state["prompt"],
                    "products": state["products"],
                    "platforms": state["platforms"],
                    "product_platforms": state.get("product_platforms", []),
                    "price_records": price_records,
                    "parallel_task_count": len(product_platforms) or len(state["products"]),
                    "source_breakdown": source_breakdown,
                },
            )
        ],
    }


def normalize_prices(state: ResearchWorkflowState) -> ResearchWorkflowState:
    llm_normalized_records, llm_stages = _llm_normalize_rows(state["prompt"], state["price_records"])
    normalized_records = normalize_price_records(llm_normalized_records)
    product_count = len({row["product_name"] for row in normalized_records})
    return {
        "price_records": normalized_records,
        "stages": llm_stages + [
            _completed_stage(
                workflow_name="price_research",
                stage_name="normalize_prices",
                message=f"已标准化 {len(normalized_records)} 条记录，覆盖 {product_count} 个产品",
                detail_json={
                    "prompt": state["prompt"],
                    "price_records": normalized_records,
                    "product_count": product_count,
                },
            )
        ]
    }


def analyze_prices(state: ResearchWorkflowState) -> ResearchWorkflowState:
    prices = [record["normalized_price"] for record in state["price_records"]]
    source_breakdown = Counter(record.get("source", "unknown") for record in state["price_records"])
    platform_sources = Counter(platform.get("source", "unknown") for platform in state["platforms"])
    warnings: list[str] = []
    average_price = round(mean(prices), 2) if prices else 0
    highest_price = max(prices) if prices else 0
    lowest_price = min(prices) if prices else 0

    if platform_sources.get("fallback_seed", 0) > 0:
        warnings.append("部分平台使用 fallback 数据")
    if not state["platforms"]:
        warnings.append("未搜索到足够的真实平台结果")
    if not state["price_records"]:
        warnings.append("未抓取到可用价格记录")
    if source_breakdown.get("default_seed", 0) > 0:
        warnings.append("部分价格来自默认种子数据")
    if any(int(record.get("attempt_count", 1)) > 1 for record in state["price_records"]):
        warnings.append("部分价格记录经过重试后获取")

    client = LLMClient()
    fallback_summary = {"warnings": warnings}
    summary_result = client.generate_json(
        f"""
你是市场调研工作流的价格分析节点。
用户输入: {state['prompt']}
统计结果:
- 样本量: {len(state['price_records'])}
- 平台数: {len(state['platforms'])}
- 均价: {average_price}
- 最高价: {highest_price}
- 最低价: {lowest_price}
- 来源分布: {dict(source_breakdown)}

任务:
补充 1 到 3 条风险提示 warnings。

返回 JSON:
{{
  "warnings": ["string"]
}}
""",
        fallback=fallback_summary,
    )
    summary_payload = summary_result.value
    final_warnings = summary_payload.get("warnings", warnings) or warnings

    price_report = {
        "currency": "CNY",
        "sample_size": len(state["price_records"]),
        "platform_count": len(state["platforms"]),
        "average_price": average_price,
        "highest_price": highest_price,
        "lowest_price": lowest_price,
        "fallback_used": bool(final_warnings),
        "warnings": final_warnings,
        "source_breakdown": dict(source_breakdown),
        "platform_source_breakdown": dict(platform_sources),
        "rows": state["price_records"],
    }
    return {
        "price_report": price_report,
        "stages": _llm_stage(
            workflow_name="price_research",
            stage_name="llm_summarize_price_risks",
            result=summary_result,
        ) + [
            _completed_stage(
                workflow_name="price_research",
                stage_name="analyze_prices",
                message=f"已生成价格报表：均价 {price_report['average_price']}，最高价 {price_report['highest_price']}，最低价 {price_report['lowest_price']}",
                detail_json=price_report,
            )
        ],
    }


def extract_business_topic(state: ResearchWorkflowState) -> ResearchWorkflowState:
    return {
        "topic": state["prompt"],
        "market_analysis": {
            "summary_json": {
                "topic": state["prompt"],
                "risks": ["平台抓取成功率不确定", "需要持续校验样本质量"],
                "opportunities": ["可快速形成价格基线", "可积累历史趋势数据"],
                "data_quality": [],
            }
        },
        "stages": [
            _completed_stage(
                workflow_name="market_analysis",
                stage_name="extract_business_topic",
                message=f"已提取商业主题：{state['prompt']}",
                detail_json={
                    "topic": state["prompt"],
                    "summary_json": {
                        "topic": state["prompt"],
                        "risks": ["平台抓取成功率不确定", "需要持续校验样本质量"],
                        "opportunities": ["可快速形成价格基线", "可积累历史趋势数据"],
                        "data_quality": [],
                    },
                },
            )
        ],
    }


def analyze_revenue_model(state: ResearchWorkflowState) -> ResearchWorkflowState:
    client = LLMClient()
    result = client.generate_structured_text(
        f"请用中文说明这个市场调研主题如何赚钱：{state['topic']}",
        fallback=f"{state['topic']} 的核心收入通常来自商品销售、增值服务与渠道分销。",
    )
    market_analysis = dict(state.get("market_analysis", {}))
    market_analysis["revenue_model_text"] = result.value
    return {
        "market_analysis": market_analysis,
        "stages": _llm_stage(
            workflow_name="market_analysis",
            stage_name="llm_analyze_revenue_model",
            result=result,
        ) + [
            _completed_stage(
                workflow_name="market_analysis",
                stage_name="analyze_revenue_model",
                message=f"已输出盈利模式摘要：{result.value[:60]}",
                detail_json={
                    "topic": state["topic"],
                    "revenue_model_text": result.value,
                },
            )
        ],
    }


def analyze_competition_and_outlook(state: ResearchWorkflowState) -> ResearchWorkflowState:
    client = LLMClient()
    result = client.generate_structured_text(
        f"请用中文简述该市场的竞争格局与前景：{state['topic']}",
        fallback=f"{state['topic']} 所在赛道竞争集中在价格、渠道效率、供应链与品牌认知，前景取决于消费升级与细分需求增长。",
    )
    market_analysis = dict(state.get("market_analysis", {}))
    market_analysis["competition_text"] = result.value
    return {
        "market_analysis": market_analysis,
        "stages": _llm_stage(
            workflow_name="market_analysis",
            stage_name="llm_analyze_competition_and_outlook",
            result=result,
        ) + [
            _completed_stage(
                workflow_name="market_analysis",
                stage_name="analyze_competition_and_outlook",
                message=f"已输出竞争与前景摘要：{result.value[:60]}",
                detail_json={
                    "topic": state["topic"],
                    "competition_text": result.value,
                },
            )
        ],
    }


def build_from_zero_plan(state: ResearchWorkflowState) -> ResearchWorkflowState:
    client = LLMClient()
    result = client.generate_structured_text(
        f"请用中文给出从0构建该商业模式的步骤：{state['topic']}",
        fallback=f"从 0 构建 {state['topic']} 可按市场验证、供应链搭建、渠道测试、成本模型优化和品牌建设五步推进。",
    )
    market_analysis = dict(state.get("market_analysis", {}))
    market_analysis["build_plan_text"] = result.value
    summary_json = dict(market_analysis.get("summary_json", {}))
    if any(platform.get("source") == "fallback_seed" for platform in state.get("platforms", [])):
        summary_json["data_quality"] = ["部分平台为 fallback 结果，需人工复核"]
    market_analysis["summary_json"] = summary_json
    return {
        "market_analysis": market_analysis,
        "stages": _llm_stage(
            workflow_name="market_analysis",
            stage_name="llm_build_from_zero_plan",
            result=result,
        ) + [
            _completed_stage(
                workflow_name="market_analysis",
                stage_name="build_from_zero_plan",
                message=f"已生成从 0 构建方案摘要：{result.value[:60]}",
                detail_json={
                    "topic": state["topic"],
                    "build_plan_text": result.value,
                    "summary_json": summary_json,
                },
            )
        ],
    }


def finalize_summary(state: ResearchWorkflowState) -> ResearchWorkflowState:
    summary = (
        f"共分析 {len(state.get('products', []))} 个产品、"
        f"{len(state.get('platforms', []))} 个平台，形成价格报表与商业模式分析。"
    )
    return {"summary": summary}


@lru_cache
def get_research_graph():
    graph = StateGraph(ResearchWorkflowState)

    graph.add_node("parse_product_intent", parse_product_intent)
    graph.add_node("discover_platforms", discover_platforms)
    graph.add_node("crawl_prices_parallel", crawl_prices_parallel)
    graph.add_node("normalize_prices", normalize_prices)
    graph.add_node("analyze_prices", analyze_prices)

    graph.add_node("extract_business_topic", extract_business_topic)
    graph.add_node("analyze_revenue_model", analyze_revenue_model)
    graph.add_node("analyze_competition_and_outlook", analyze_competition_and_outlook)
    graph.add_node("build_from_zero_plan", build_from_zero_plan)

    graph.add_node("finalize_summary", finalize_summary)

    graph.add_edge(START, "parse_product_intent")
    graph.add_edge(START, "extract_business_topic")

    graph.add_edge("parse_product_intent", "discover_platforms")
    graph.add_edge("discover_platforms", "crawl_prices_parallel")
    graph.add_edge("crawl_prices_parallel", "normalize_prices")
    graph.add_edge("normalize_prices", "analyze_prices")

    graph.add_edge("extract_business_topic", "analyze_revenue_model")
    graph.add_edge("analyze_revenue_model", "analyze_competition_and_outlook")
    graph.add_edge("analyze_competition_and_outlook", "build_from_zero_plan")

    graph.add_edge("analyze_prices", "finalize_summary")
    graph.add_edge("build_from_zero_plan", "finalize_summary")
    graph.add_edge("finalize_summary", END)

    return graph.compile()


def run_research_workflow(prompt: str) -> WorkflowResult:
    result = get_research_graph().invoke({"prompt": prompt, "stages": []})
    return WorkflowResult(
        products=result.get("products", []),
        platforms=result.get("platforms", []),
        price_records=result.get("price_records", []),
        price_report=result.get("price_report", {}),
        market_analysis=result.get("market_analysis", {}),
        stages=result.get("stages", []),
        summary=result.get("summary", ""),
    )
