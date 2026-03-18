# LLM Provider Design

**Goal:** 在不改 LangGraph 节点提示词与调用方式的前提下，为后端同时支持 Kimi 与火山方舟两个大模型 provider，并保留现有 fallback 与错误提示链路。

## Design

- 保留现有 `LLMResult` 返回协议，继续承载 `success`、`fallback`、`error` 三类结果。
- 新增统一门面 `backend/src/app/services/llm_client.py`，由 `Settings.llm_provider` 选择底层 provider。
- 保留现有 `KimiClient`，新增 `VolcengineArkClient`，两者都通过 OpenAI 兼容 SDK 调用。
- LangGraph 工作流只依赖 `LLMClient`，不再直接绑定具体 provider。

## Configuration

- 新增 `LLM_PROVIDER`，允许 `kimi` 或 `volcengine`。
- 保留 Kimi 配置：`KIMI_API_KEY`、`KIMI_BASE_URL`、`KIMI_MODEL`。
- 新增火山方舟配置：`ARK_API_KEY`、`ARK_BASE_URL`、`ARK_MODEL`。
- 若所选 provider 未配置 key，则继续走 fallback，并在 stage 中提示模型未启用。

## Testing

- 增加 provider 选择测试。
- 增加火山方舟未配置时的 fallback 测试。
- 保持现有工作流 fallback / error stage 测试，但改为打桩统一 `LLMClient`。

## Docs

- 更新 `.env.example`。
- 更新 `README.md` 的 LLM 配置说明。
- 更新 `docs/execution-status.md` 的当前实现描述。
