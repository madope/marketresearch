# Volcengine Web Search Discovery Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `discover_platforms` 接入火山方舟原生 `web_search`，让平台发现基于实时搜索结果而不是经验推断，同时返回平台名称、主域名、平台简介和真实价格页 URL；最多搜索 3 轮，目标至少 10 个平台，不补假数据；`crawl_prices_parallel` 直接抓取这些 `platform_url`。

**Architecture:** 在统一 LLM client 层增加 `search_web` 能力，`discover_platforms` 优先使用 web search 返回的平台列表、evidence、`platform_url` 和 `platform_summary`。节点会按去重结果最多执行 3 轮搜索，不足 10 个时继续补搜，但永不使用假平台数据。`crawl_prices_parallel` 优先使用 `platform_url` 进行 HTML 抓取。Kimi 暂时显式 fallback，不猜测未确认的原生搜索接口。

**Tech Stack:** Python, LangGraph, OpenAI-compatible Responses API, pytest

---

## Chunk 1: Tests

### Task 1: Add search_web tests

**Files:**
- Modify: `backend/tests/test_llm_client.py`
- Modify: `backend/tests/test_workflow.py`
- Modify: `backend/tests/test_services.py`

- [ ] Step 1: Write failing tests for Volcengine web search success
- [ ] Step 2: Write failing tests for Kimi fallback behavior
- [ ] Step 3: Write failing tests for workflow evidence propagation
- [ ] Step 4: Write failing tests for 3 轮 web search、真实 `platform_url` 抓取和“永不补假数据”

## Chunk 2: Implementation

### Task 2: Add provider web search support

**Files:**
- Modify: `backend/src/app/services/llm_client.py`
- Modify: `backend/src/app/services/ark_client.py`
- Modify: `backend/src/app/services/crawl_service.py`
- Modify: `backend/src/app/services/kimi_client.py`
- Modify: `backend/src/app/models/research.py`
- Modify: `backend/src/app/api/routes.py`
- Modify: `backend/src/app/schemas/research.py`
- Modify: `backend/src/app/workflows/research_workflow.py`

- [ ] Step 1: Add `search_web` interface to unified client
- [ ] Step 2: Implement Volcengine `Responses API + web_search`
- [ ] Step 3: Add explicit Kimi fallback for this capability
- [ ] Step 4: Switch `discover_platforms` to emit `platform_url` / `platform_summary` and run up to 3 search rounds
- [ ] Step 5: Update `crawl_prices_parallel` and `PriceCrawlerService` to prefer `platform_url`
- [ ] Step 6: Persist `platform_url` / `platform_summary` in task detail

## Chunk 3: Verification

### Task 3: Verify

**Files:**
- Verify only

- [ ] Step 1: Run targeted web search tests
- [ ] Step 2: Run `cd backend && ./.venv/bin/python -m pytest tests/test_workflow.py tests/test_services.py tests/test_research_service.py tests/test_api.py`
