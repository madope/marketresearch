# Research Intake Chat Design

## Goal

将现有单个 `prompt` 输入框改成“需求澄清对话”模式。在真正创建 LangGraph 调研任务前，先通过 LLM 对话确认：

- 调研地区
- 调研商品
- 调研目标

当信息足够完整时，再生成最终调研 prompt 并沿用现有 `POST /api/research-tasks`。

## Scope

- 新增后端接口 `POST /api/research-intake/chat`
- 新增前端 intake 对话状态
- 将“发起调研”卡片改成对话式需求澄清 UI
- 保持现有 LangGraph 主工作流不变

## API Contract

请求：

```json
{
  "messages": [
    { "role": "user", "content": "我想调研中国大陆宠物烘干箱市场" }
  ],
  "draft_requirement": {
    "market_topic": "",
    "target_region": "",
    "products": [],
    "goals": [],
    "constraints": {}
  }
}
```

响应：

```json
{
  "assistant_message": "还需要确认：更关注价格、平台分布，还是市场可行性？",
  "draft_requirement": {
    "market_topic": "中国大陆宠物烘干箱市场",
    "target_region": "中国大陆",
    "products": ["宠物烘干箱"],
    "goals": [],
    "constraints": {}
  },
  "missing_fields": ["goals"],
  "ready_to_start": false,
  "final_prompt": ""
}
```

## LLM Integration

- 使用统一 `LLMClient.generate_json(...)`
- LLM 输出结构化 JSON：
  - `assistant_message`
  - `draft_requirement`
  - `missing_fields`
  - `ready_to_start`
  - `final_prompt`
- 当 LLM 不可用或返回格式异常时，使用基于关键词的 deterministic fallback，仅从用户已输入内容提取，不补虚构信息

## Frontend Flow

1. 用户发送一条 intake 消息
2. 前端调用 `POST /api/research-intake/chat`
3. 追加 assistant 回复
4. 在前端内部更新需求草稿与缺失字段
5. `ready_to_start=true` 时启用“开始调研”
6. 不展示单独的“已确认需求”摘要卡；当信息足够时，由 assistant 消息直接提示用户点击下方按钮开始调研
7. 点击“开始调研”后，使用 `final_prompt` 调用现有创建任务接口

## Non-goals

- 不保存 intake 会话到数据库
- 不把 intake 本身做成 LangGraph
- 不改现有调研任务执行链路
