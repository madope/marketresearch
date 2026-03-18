# Backend Debug Logging Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为后端增加只记录工作流和 LLM 调用的文件日志，输出到 `backend/logs/app.log`。

**Architecture:** 增加独立应用 logger，不与 `uvicorn` access log 混用。工作流节点和 LLM 客户端分别写摘要日志，避免记录过大的原始输入。

**Tech Stack:** Python logging, FastAPI, LangGraph, pytest

---

## Chunk 1: Tests

### Task 1: Add logging tests

**Files:**
- Create: `backend/tests/test_logging.py`
- Modify: `backend/tests/test_llm_client.py`
- Modify: `backend/tests/test_workflow.py`

- [ ] Step 1: Write failing tests for log file creation
- [ ] Step 2: Write failing tests for LLM call logging
- [ ] Step 3: Write failing tests for workflow node logging

## Chunk 2: Implementation

### Task 2: Add file logger and integrate it

**Files:**
- Create: `backend/src/app/core/logging.py`
- Modify: `backend/src/app/core/config.py`
- Modify: `backend/src/app/main.py`
- Modify: `backend/src/app/services/kimi_client.py`
- Modify: `backend/src/app/services/ark_client.py`
- Modify: `backend/src/app/workflows/research_workflow.py`

- [ ] Step 1: Configure app file logger
- [ ] Step 2: Initialize logger during app startup
- [ ] Step 3: Add LLM call logs
- [ ] Step 4: Add workflow node logs

## Chunk 3: Verification

### Task 3: Verify

**Files:**
- Verify only

- [ ] Step 1: Run targeted logging tests
- [ ] Step 2: Run `cd backend && ./.venv/bin/python -m pytest -q`
- [ ] Step 3: Trigger a real task and inspect `backend/logs/app.log`
