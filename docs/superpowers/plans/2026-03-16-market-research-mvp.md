# 市场调研网站 MVP 实施计划

## Summary

**目标**  
构建一个前后端分离的市场调研网站：用户输入调研主题后，后端触发 LangGraph 工作流并行完成价格调研与商业模式分析，结果保存到 SQLite，并在 React 前端展示和回看历史记录。

**架构**  
采用 `React + Vite + TypeScript` 前端，`FastAPI + LangGraph + SQLAlchemy` 后端，`SQLite` 持久化。前端通过 REST API 提交任务并轮询状态；后端以单体服务方式承载 API、工作流编排、抓取、分析和存储。

**Tech Stack**
- Frontend: React, Vite, TypeScript, React Router, TanStack Query, ECharts, CSS Modules
- Backend: Python 3.11+, FastAPI, Pydantic, LangGraph, SQLAlchemy, Alembic, httpx, BeautifulSoup4, Playwright
- LLM: 可切换 provider 的兼容接口调用（Kimi / 火山方舟）
- Database: SQLite

## Key Changes

### 1. 项目结构与基础工程
- 建立根目录结构：`frontend/`、`backend/`、`docs/`、`assets/`
- 前端初始化 Vite React TS 项目；后端初始化 FastAPI 项目
- 补齐根级 `README.md`、`.env.example`、开发启动说明
- 本地开发按“仅本地开发运行”规划，不包含生产部署和 Docker Compose

### 2. 后端服务与 LangGraph 编排
- 在 `backend/src/app/main.py` 暴露 FastAPI 应用与基础路由
- 在 `backend/src/app/api/` 定义 REST API：
  - `POST /api/research-tasks`
  - `GET /api/research-tasks`
  - `GET /api/research-tasks/{task_id}`
  - `GET /api/research-tasks/{task_id}/status`
  - `GET /api/health`
- 在 `backend/src/app/workflows/` 建立 LangGraph 图：
  - `price_research_graph`
  - `market_analysis_graph`
  - 顶层 `research_graph` 并行调度两个子图
- 价格工作流节点固定为：
  - `parse_product_intent`
  - `select_products`
  - `discover_platforms`
  - `crawl_prices_parallel`
  - `normalize_prices`
  - `analyze_prices`
  - `persist_price_report`
- 商业模式工作流节点固定为：
  - `extract_business_topic`
  - `analyze_revenue_model`
  - `analyze_competition_and_outlook`
  - `build_from_zero_plan`
  - `persist_market_analysis`
- 平台发现与价格抓取节点内置最多 3 次重试；不足 5 个平台时任务可完成，但必须写入覆盖不足说明
- LLM 调用封装为独立客户端，支持按配置切换 provider，所有提示词模板集中放在 `backend/src/app/prompts/`

### 3. 抓取、清洗与分析实现
- 抓取目标市场固定为中国大陆
- 平台发现采用通用网页搜索优先，不依赖第三方采集服务
- 抓取实现分层：
  - 搜索与平台发现服务
  - 商品页抓取服务
  - 价格解析与标准化服务
- 并发粒度为“产品 x 平台”
- 统一标准化字段：
  - `task_id`
  - `product_name`
  - `product_source_type`
  - `platform_name`
  - `platform_domain`
  - `product_url`
  - `raw_title`
  - `spec_text`
  - `currency`
  - `raw_price`
  - `normalized_price`
  - `price_unit`
  - `captured_at`
  - `confidence_score`
  - `is_outlier`
- 价格分析输出至少包含：
  - 均价
  - 最高价
  - 最低价
  - 样本数
  - 平台数
  - 价格区间
  - 异常值说明
  - 缺失/失败说明

### 4. SQLite 数据模型
- `research_tasks`
- `research_task_stages`
- `research_products`
- `research_platforms`
- `price_records`
- `price_reports`
- `market_analysis_reports`

### 5. 前端信息架构与页面实现
- 前端主页面采用 `A 指挥台式布局`
- 左侧固定 `历史记录区`
- 右侧主工作区分 4 块：
  - `任务输入区`
  - `任务进度区`
  - `结果展示区`
  - `任务摘要区`
- 结果展示区采用双栏：
  - 左栏：商业模式分析结果
  - 右栏：价格统计卡片 + 价格表格 + 图表
- 页面组件建议拆分为：
  - `ResearchInputPanel`
  - `TaskProgressPanel`
  - `PriceReportPanel`
  - `MarketAnalysisPanel`
  - `HistorySidebar`
  - `TaskSummaryPanel`
- 前端通过 TanStack Query 处理：
  - 创建任务 mutation
  - 历史任务查询
  - 任务详情查询
  - 任务状态轮询
- 科技风视觉固定为：
  - 深海蓝渐变背景
  - 青绿/冰蓝强调色
  - 玻璃拟态深色卡片
  - 扫描线与淡入动效
  - 非紫色主视觉

### 6. Public APIs / Interfaces
- `POST /api/research-tasks`
- `GET /api/research-tasks`
- `GET /api/research-tasks/{task_id}/status`
- `GET /api/research-tasks/{task_id}`

## Test Plan

- 后端单元测试：
  - 品类输入最多返回 5 个代表产品
  - 具体产品输入不增不减
  - 任务详情返回完整价格报表与市场分析
- 后端集成测试：
  - 创建任务后能写入 `research_tasks`
  - 任务完成后详情接口能返回完整聚合结果
- 前端组件测试：
  - 提交输入后触发回调
  - Dashboard 正确渲染历史区和结果区
- 前后端联调测试：
  - 从输入提示词到页面展示完整结果端到端跑通

## Assumptions

- 首版为单用户内部工具，不做登录、权限和数据隔离
- 首版仅覆盖中国大陆市场与人民币价格
- 首版使用 REST + 轮询，不做 WebSocket 流式输出
- 首版按本地开发运行规划，不包含生产部署方案
- 首版允许部分平台抓取失败，只要能返回可解释的结果就算任务成功
- LLM provider 凭证通过 `.env` 注入
