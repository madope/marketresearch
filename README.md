# Market Research MVP

一个前后端分离的市场调研网站。用户提交调研主题后，后端触发 LangGraph 工作流并行生成价格报表与商业模式分析，结果保存数据库并在前端展示。

## 目录结构

```text
backend/   Python + FastAPI + LangGraph
frontend/  React + Vite + TypeScript
docs/      计划与设计文档
assets/    静态资源与示例数据
```

## 本地开发

### 1. 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
/Users/cxxhb/projects/marketresearch/backend/.venv/bin/playwright install chromium
/Users/cxxhb/projects/marketresearch/backend/.venv/bin/alembic upgrade head
uvicorn app.main:app --reload
```

默认使用 `sqlite:///./marketresearch.db`，SQLite 作为后端主数据库。若需调整数据库文件位置，可在环境变量中设置 `DATABASE_URL`。

大模型默认 provider 为 `kimi`，可通过 `LLM_PROVIDER` 在 `kimi` 与 `volcengine` 间切换：

```bash
LLM_PROVIDER=kimi
KIMI_API_KEY=...
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL=kimi-k2-0905-preview
```

```bash
LLM_PROVIDER=volcengine
ARK_API_KEY=...
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_MODEL=<your-ark-endpoint-id>
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认请求 `http://localhost:8000/api`，也可通过 `VITE_API_BASE_URL` 覆盖。

## 测试

### 后端

```bash
cd backend
pytest
```

### SQLite Migration

```bash
cd backend
.venv/bin/alembic upgrade head
```

### 前端

```bash
cd frontend
npm test
```

## 当前实现范围

- 任务创建、历史记录、详情查询
- LangGraph 风格的双工作流研究管线骨架
- 价格报表和商业模式分析结果落库
- 科技风 Dashboard 界面
- 双 provider LLM 客户端封装（Kimi / 火山方舟）与本地 fallback
- `discover_platforms` 通过 Volcengine `web_search` 联网搜索平台名称、域名、简介和真实价格页 URL
- `discover_platforms` 对每一种商品分别执行最多 3 轮搜索，目标为该商品收集至少 10 个真实平台结果；不足时只返回真实搜到的数据，不补假数据
- `crawl_prices_parallel` 为每种商品创建一个并行抓取任务，每个任务只访问该商品自己的平台价格页 URL
- 价格抓取链路为 `Playwright 抓网页 -> HTML 转 Markdown -> LLM 抽取价格`，输出保留每个平台的 `product_url`
- 如果网页抓取失败，或网页已抓到但 LLM 未识别出价格，仍保留该平台记录，价格为空，并写明失败原因
- 任务进度中的每个步骤支持展开查看结构化详情，优先展示 stage `detail_json`，可看到平台列表、价格记录、价格报表、商业分析文本，以及 LLM 节点的 provider / prompt / result 摘要

## 后续优先项

- 接入真实 LangGraph StateGraph
- 接入真实大模型结构化输出
- 扩展更多平台的真实商品页抓取与页面解析
- 增加 Alembic migration 与 SQLite schema 管理
