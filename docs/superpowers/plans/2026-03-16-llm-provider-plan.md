# LLM Provider Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 LangGraph 工作流增加 Kimi 与火山方舟双 provider 支持，并同步更新配置与说明文档。

**Architecture:** 在服务层增加统一 `LLMClient` 门面，内部按配置分发到 `KimiClient` 或 `VolcengineArkClient`。工作流继续只消费统一接口，保留现有 fallback 与错误 stage 逻辑。

**Tech Stack:** Python, FastAPI, LangGraph, OpenAI SDK compatible API, pytest

---

## Chunk 1: Provider Abstraction

### Task 1: Add provider selection tests

**Files:**
- Create: `backend/tests/test_llm_client.py`
- Modify: `backend/tests/test_workflow.py`

- [ ] Step 1: Write failing tests for provider selection and workflow patch points
- [ ] Step 2: Run `cd backend && ./.venv/bin/python -m pytest tests/test_llm_client.py tests/test_workflow.py`
- [ ] Step 3: Confirm tests fail because `LLMClient` does not exist yet

### Task 2: Implement provider abstraction

**Files:**
- Create: `backend/src/app/services/ark_client.py`
- Create: `backend/src/app/services/llm_client.py`
- Modify: `backend/src/app/workflows/research_workflow.py`
- Modify: `backend/src/app/core/config.py`

- [ ] Step 1: Add `VolcengineArkClient` with `generate_json` and `generate_structured_text`
- [ ] Step 2: Add `LLMClient` facade and provider dispatch
- [ ] Step 3: Switch workflow to use `LLMClient`
- [ ] Step 4: Run `cd backend && ./.venv/bin/python -m pytest tests/test_llm_client.py tests/test_workflow.py`

## Chunk 2: Docs And Config

### Task 3: Update runtime configuration docs

**Files:**
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/execution-status.md`
- Create: `docs/superpowers/specs/2026-03-16-llm-provider-design.md`

- [ ] Step 1: Document `LLM_PROVIDER`, Kimi config, and Ark config
- [ ] Step 2: Update execution status to reflect multi-provider support
- [ ] Step 3: Keep terminology consistent as `LLM` instead of only `Kimi`

## Chunk 3: Final Verification

### Task 4: Run full backend verification

**Files:**
- Verify only

- [ ] Step 1: Run `cd backend && ./.venv/bin/python -m pytest -q`
- [ ] Step 2: Confirm all tests pass
- [ ] Step 3: Report any remaining warnings separately from pass/fail status
