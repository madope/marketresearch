# LLM Platform Discovery Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `discover_platforms` 节点由 LLM 直接决定最终平台列表，并保留去重、校验和 fallback 补齐到 10 个平台的能力。

**Architecture:** 工作流内新增 LLM 最终平台选择函数，直接返回平台对象列表。程序层验证域名并在结果不足时回退到 `PlatformDiscoveryService` 的 fallback 平台集。

**Tech Stack:** Python, LangGraph, OpenAI-compatible LLM client, pytest

---

## Chunk 1: Tests

### Task 1: Add workflow tests for LLM-driven platform discovery

**Files:**
- Modify: `backend/tests/test_workflow.py`

- [ ] Step 1: Write failing tests for LLM-selected final platforms
- [ ] Step 2: Run `cd backend && ./.venv/bin/python -m pytest tests/test_workflow.py::test_discover_platforms_uses_llm_selected_final_platforms tests/test_workflow.py::test_discover_platforms_filters_invalid_llm_domains_and_backfills`
- [ ] Step 3: Confirm tests fail before implementation

## Chunk 2: Implementation

### Task 2: Implement LLM final platform selection

**Files:**
- Modify: `backend/src/app/workflows/research_workflow.py`
- Modify: `backend/src/app/services/discovery_service.py`

- [ ] Step 1: Add domain validation and LLM platform selection helper
- [ ] Step 2: Change `discover_platforms` to return up to 10 platforms
- [ ] Step 3: Filter duplicates/invalid domains and backfill with fallback platforms
- [ ] Step 4: Run targeted workflow tests

## Chunk 3: Docs

### Task 3: Sync docs

**Files:**
- Create: `docs/superpowers/specs/2026-03-17-llm-platform-discovery-design.md`
- Create: `docs/superpowers/plans/2026-03-17-llm-platform-discovery-plan.md`

- [ ] Step 1: Record the updated node behavior
- [ ] Step 2: Record constraints and failure handling
