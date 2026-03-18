# Backend Debug Logging Design

**Goal:** 为后端增加独立的文件日志，只记录工作流节点和 LLM 调用，便于排查 LangGraph 与大模型相关问题。

## Scope

- 只记录后端工作流和 LLM 调用
- 不记录前端日志
- 不接入 `uvicorn` access log
- 不落库，只写文件

## Log Target

- 日志目录：`backend/logs/`
- 日志文件：`backend/logs/app.log`

## Logged Events

- Workflow:
  - 节点开始
  - 节点结束
  - 输入摘要
  - 输出摘要
- LLM:
  - provider
  - model
  - method (`text` / `json`)
  - status (`success` / `fallback` / `error`)
  - elapsed_ms
  - 简短错误信息
  - prompt 摘要
