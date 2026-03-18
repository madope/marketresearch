# Playwright Crawl Prices Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `crawl_prices_parallel` 重构为按商品并行运行的 `Playwright + Markdown + LLM` 价格抓取链路。

**Architecture:** 为每个商品单独创建抓取任务，只在该商品自己的平台集合中抓页面。页面通过 Playwright 获取 HTML，再转换为 Markdown，并交给 LLM 提取价格；抓取失败或未识别出价格时仍保留一条记录。

**Tech Stack:** Python, FastAPI, LangGraph, Playwright, BeautifulSoup, OpenAI-compatible LLM client, pytest

---

## Chunk 1: 抓取服务

### Task 1: 新增网页抓取与 Markdown 转换服务

**Files:**
- Create: `backend/src/app/services/page_fetch_service.py`
- Test: `backend/tests/test_services.py`

- [ ] Step 1: 写失败测试，验证 Playwright 抓取结果会返回 `final_url/html/markdown/status/error_message`
- [ ] Step 2: 运行测试确认失败
- [ ] Step 3: 用同步 Playwright API 实现最小抓取服务和 HTML 转 Markdown
- [ ] Step 4: 运行测试确认通过

## Chunk 2: 价格抽取链路

### Task 2: 为单个平台引入 `Markdown -> LLM 价格提取`

**Files:**
- Modify: `backend/src/app/services/crawl_service.py`
- Modify: `backend/src/app/workflows/research_workflow.py`
- Test: `backend/tests/test_services.py`

- [ ] Step 1: 写失败测试，验证抓取成功但未识别价格时仍保留空价格记录和原因
- [ ] Step 2: 运行测试确认失败
- [ ] Step 3: 实现单个平台处理链路和 LLM 提取
- [ ] Step 4: 运行测试确认通过

## Chunk 3: 并行商品任务

### Task 3: 将 `crawl_prices_parallel` 改成按商品并行

**Files:**
- Modify: `backend/src/app/workflows/research_workflow.py`
- Test: `backend/tests/test_workflow.py`

- [ ] Step 1: 写失败测试，验证每个商品创建一个并行任务且只抓自己的平台
- [ ] Step 2: 运行测试确认失败
- [ ] Step 3: 用线程池实现按商品并行抓取并汇总结果
- [ ] Step 4: 运行测试确认通过

## Chunk 4: 文档与验证

### Task 4: 同步文档并全量回归

**Files:**
- Modify: `README.md`
- Add: `docs/superpowers/specs/2026-03-18-playwright-crawl-prices-design.md`

- [ ] Step 1: 同步 README 和设计文档
- [ ] Step 2: 运行 `pytest tests/test_workflow.py tests/test_services.py tests/test_research_service.py tests/test_api.py -q`
- [ ] Step 3: 重启后端并验证新任务链路
