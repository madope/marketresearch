# Stage Detail JSON Design

## 目标

为任务进度里的每个步骤保存结构化详情，前端点击“查看详情”时，不再只显示 `stage.message`，而是优先显示该步骤的完整输出摘要。

## 方案

- 在 `research_task_stages` 表新增 `detail_json`
- 后端每次持久化 stage 时一并保存 `detail_json`
- 前端任务详情接口返回 `detail_json`
- 前端详情面板优先展示 `detail_json` 的格式化 JSON；没有时回退到 `stage.message`

## 详情内容

- `parse_product_intent`
  - `prompt`
  - `intent_type`
  - `products`
- `select_products`
  - `selected_products`
- `discover_platforms`
  - `products`
  - `platforms`
  - `metrics`
- `crawl_prices_parallel`
  - `products`
  - `platforms`
  - `price_records`
- `normalize_prices`
  - `price_records`
- `analyze_prices`
  - `price_report`
- 商业分析节点
  - 对应文本输出
  - `summary_json`
- LLM fallback/error 节点
  - `provider`
  - `model`
  - `method`
  - `prompt`
  - `result`
  - `status`
  - `message`

## 运行中节点

运行中的步骤只保存最小详情：

```json
{
  "node_name": "discover_platforms",
  "status": "running"
}
```

## 兼容性

- 旧任务没有 `detail_json`
- 前端自动回退到 `stage.message`
- 需要 Alembic migration 为 SQLite 增加列
