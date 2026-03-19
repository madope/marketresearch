from __future__ import annotations

import json
import re
from typing import Any

from app.schemas.research import IntakeMessage, ResearchRequirementDraft
from app.services.llm_client import LLMClient

GOAL_KEYWORDS: list[tuple[str, str]] = [
    ("价格", "价格调研"),
    ("售价", "价格调研"),
    ("平台", "平台分布"),
    ("渠道", "平台分布"),
    ("值不值得做", "市场可行性分析"),
    ("能不能做", "市场可行性分析"),
    ("可行", "市场可行性分析"),
    ("怎么赚钱", "商业模式分析"),
    ("盈利", "商业模式分析"),
]

REGION_KEYWORDS = [
    "中国大陆",
    "中国",
    "北美",
    "美国",
    "欧洲",
    "东南亚",
    "全球",
]

PRODUCT_HINTS = ("烘干箱", "牙刷", "喂食器", "猫砂盆", "耳机", "手机", "玩具", "猫粮", "狗粮")


def chat_research_intake(
    messages: list[IntakeMessage],
    draft_requirement: ResearchRequirementDraft,
) -> dict[str, Any]:
    fallback = _build_fallback_response(messages, draft_requirement)
    client = LLMClient()
    prompt = _build_intake_prompt(messages, draft_requirement)
    result = client.generate_json(prompt, fallback)
    payload = result.value if isinstance(result.value, dict) else fallback
    return _normalize_intake_payload(payload, draft_requirement)


def _build_intake_prompt(messages: list[IntakeMessage], draft_requirement: ResearchRequirementDraft) -> str:
    conversation = "\n".join(f"{message.role}: {message.content}" for message in messages[-12:])
    return f"""
你是市场调研需求澄清助手。你的任务是：
1. 从用户对话中提取并更新结构化调研需求
2. 判断是否还缺关键信息
3. 如果信息不足，只追问最关键的 1-2 个问题
4. 如果信息足够，明确告知可以开始调研
5. 不要编造用户未明确表达的事实
6. 只返回合法 JSON，不要输出 Markdown

结构化字段说明：
- market_topic: 规范化后的调研主题
- target_region: 调研地区
- products: 商品列表
- goals: 调研目标列表，可选值包括 价格调研 / 平台分布 / 市场可行性分析 / 商业模式分析
- constraints: 约束条件

当 target_region、products、goals 都已具备时，ready_to_start 应为 true。

当前对话：
{conversation}

当前草稿：
{json.dumps(draft_requirement.model_dump(), ensure_ascii=False)}

请输出：
{{
  "assistant_message": "给用户的回复",
  "draft_requirement": {{
    "market_topic": "",
    "target_region": "",
    "products": [],
    "goals": [],
    "constraints": {{}}
  }},
  "missing_fields": [],
  "ready_to_start": false,
  "final_prompt": ""
}}
""".strip()


def _build_fallback_response(
    messages: list[IntakeMessage],
    draft_requirement: ResearchRequirementDraft,
) -> dict[str, Any]:
    combined_text = " ".join(message.content for message in messages if message.role == "user")
    merged = draft_requirement.model_copy(deep=True)

    if not merged.target_region:
        for region in REGION_KEYWORDS:
            if region in combined_text:
                merged.target_region = region
                break

    if not merged.products:
        products = _extract_products(combined_text)
        if products:
            merged.products = products

    merged.goals = _merge_unique(merged.goals, _extract_goals(combined_text))

    if not merged.market_topic:
        topic_parts = [part for part in [merged.target_region, "、".join(merged.products)] if part]
        if topic_parts:
            merged.market_topic = f"{''.join(topic_parts)}市场"

    missing_fields = _compute_missing_fields(merged)
    ready_to_start = not missing_fields
    final_prompt = _build_final_prompt(merged) if ready_to_start else ""

    return {
        "assistant_message": _build_assistant_message(merged, missing_fields, ready_to_start),
        "draft_requirement": merged.model_dump(),
        "missing_fields": missing_fields,
        "ready_to_start": ready_to_start,
        "final_prompt": final_prompt,
    }


def _extract_products(text: str) -> list[str]:
    candidates: list[str] = []
    for match in re.findall(r"调研([^，。；,.]+)", text):
        cleaned = _clean_product_candidate(match)
        if cleaned and cleaned not in candidates:
            candidates.append(cleaned)
    for match in re.findall(r"看([^，。；,.]+)", text):
        cleaned = _clean_product_candidate(match)
        if cleaned and "价格" not in cleaned and "平台" not in cleaned and cleaned not in candidates:
            candidates.append(cleaned)
    explicit = re.split(r"[，,、/]|和", text)
    for chunk in explicit:
        cleaned = _clean_product_candidate(chunk)
        if cleaned and cleaned not in candidates:
            candidates.append(cleaned)
    return candidates[:5]


def _clean_product_candidate(text: str) -> str:
    cleaned = re.sub(r"^(主要|重点|看|调研|想看|想调研|我想调研|我想看)", "", text).strip()
    cleaned = cleaned.replace("市场", "").replace("中国大陆", "").replace("中国", "").strip()
    if not cleaned or cleaned in {"宠物", "数码", "家电"}:
        return ""
    if any(keyword in cleaned for keyword in PRODUCT_HINTS):
        return cleaned
    return ""


def _extract_goals(text: str) -> list[str]:
    goals: list[str] = []
    for keyword, goal in GOAL_KEYWORDS:
        if keyword in text and goal not in goals:
            goals.append(goal)
    return goals


def _merge_unique(existing: list[str], incoming: list[str]) -> list[str]:
    merged = list(existing)
    for item in incoming:
        if item and item not in merged:
            merged.append(item)
    return merged


def _compute_missing_fields(draft_requirement: ResearchRequirementDraft) -> list[str]:
    missing_fields: list[str] = []
    if not draft_requirement.target_region:
        missing_fields.append("target_region")
    if not draft_requirement.products:
        missing_fields.append("products")
    if not draft_requirement.goals:
        missing_fields.append("goals")
    return missing_fields


def _build_assistant_message(
    draft_requirement: ResearchRequirementDraft,
    missing_fields: list[str],
    ready_to_start: bool,
) -> str:
    if ready_to_start:
        topic = draft_requirement.market_topic or "这次调研"
        return f"我已经理解你的需求，接下来会围绕{topic}展开分析。请点击下方按钮开始调研。"

    questions: list[str] = []
    if "target_region" in missing_fields:
        questions.append("你想调研哪个地区")
    if "products" in missing_fields:
        questions.append("主要关注哪些商品")
    if "goals" in missing_fields:
        questions.append("更关注价格、平台分布，还是市场可行性")
    if questions:
        return "还需要确认：" + "；".join(questions) + "？"
    return "请继续补充你的调研需求。"


def _build_final_prompt(draft_requirement: ResearchRequirementDraft) -> str:
    product_text = "、".join(draft_requirement.products)
    goal_text = "、".join(draft_requirement.goals)
    topic = draft_requirement.market_topic or f"{draft_requirement.target_region}{product_text}市场"
    return f"调研{topic}，重点分析{product_text}的{goal_text}。"


def _normalize_intake_payload(
    payload: dict[str, Any],
    draft_requirement: ResearchRequirementDraft,
) -> dict[str, Any]:
    raw_draft = payload.get("draft_requirement") or {}
    normalized_draft = ResearchRequirementDraft(
        market_topic=str(raw_draft.get("market_topic") or draft_requirement.market_topic or ""),
        target_region=str(raw_draft.get("target_region") or draft_requirement.target_region or ""),
        products=[str(item) for item in raw_draft.get("products", draft_requirement.products or []) if str(item).strip()],
        goals=[str(item) for item in raw_draft.get("goals", draft_requirement.goals or []) if str(item).strip()],
        constraints=raw_draft.get("constraints", draft_requirement.constraints or {}) or {},
    )
    missing_fields = _compute_missing_fields(normalized_draft)
    ready_to_start = not missing_fields
    final_prompt = str(payload.get("final_prompt") or "").strip()
    if ready_to_start and not final_prompt:
        final_prompt = _build_final_prompt(normalized_draft)
    assistant_message = str(payload.get("assistant_message") or "").strip()
    if ready_to_start:
        assistant_message = _build_assistant_message(normalized_draft, missing_fields, ready_to_start)
    elif not assistant_message:
        assistant_message = _build_assistant_message(normalized_draft, missing_fields, ready_to_start)
    return {
        "assistant_message": assistant_message,
        "draft_requirement": normalized_draft.model_dump(),
        "missing_fields": missing_fields,
        "ready_to_start": ready_to_start,
        "final_prompt": final_prompt,
    }
