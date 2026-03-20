# 局域网访问开发模式 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为前端新增可选的局域网访问启动模式，同时保持默认本地开发行为不变。

**Architecture:** 通过新增 `dev:lan` 脚本让 Vite 绑定到 `0.0.0.0`，并把前端默认 API 地址统一成相对路径 `/api`，再由 Vite 代理到本机 FastAPI。这样局域网设备只需访问前端端口即可完整使用页面。

**Tech Stack:** React, Vite, TypeScript, FastAPI, README 文档

---

## Chunk 1: Frontend LAN Mode

### Task 1: 新增局域网前端启动命令

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: 新增 `dev:lan` 脚本**
- [ ] **Step 2: 保留默认 `dev` 脚本不变**

### Task 2: 统一前端 API 到相对路径并配置代理

**Files:**
- Modify: `frontend/src/features/research/api.ts`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/vite.config.js`

- [ ] **Step 1: 将默认 API 地址改为 `/api`**
- [ ] **Step 2: 为 Vite 开发服务器增加 `/api` 代理到 `http://127.0.0.1:8000`**
- [ ] **Step 3: 保持现有测试配置不变**

## Chunk 2: Documentation

### Task 3: 补充 README 使用说明

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新前端 API 说明**
- [ ] **Step 2: 新增加局域网访问步骤**
- [ ] **Step 3: 说明为什么不需要修改后端地址**

## Chunk 3: Verification

### Task 4: 验证现有前端测试

**Files:**
- Test: `frontend/tests/app.test.tsx`

- [ ] **Step 1: 运行 `cd frontend && npm test -- --run tests/app.test.tsx`**
- [ ] **Step 2: 确认通过**

Plan complete and saved to `docs/superpowers/plans/2026-03-19-lan-access-dev-mode-plan.md`. Ready to execute?
