# Playwright Crawl Prices Design

## 背景

原有 `crawl_prices_parallel` 主要依赖固定 URL 模板和轻量 HTML 选择器抽取价格，无法满足“每个商品在自己的真实平台页面上抓取价格”的要求，也难以保留网页抓取上下文供调试查看。

## 目标

将价格抓取链路重构为：

1. 每个商品创建一个并行任务。
2. 每个商品只处理自己在 `discover_platforms` 中搜索到的平台价格页。
3. 使用 Playwright 抓取网页内容。
4. 将网页 HTML 转换为 Markdown。
5. 通过 LLM 从 Markdown 中抽取商品价格。
6. 输出每个商品在每个平台上的价格结果，并保留价格页 URL。

## 设计

### 商品级并行

- `discover_platforms` 产出 `product_platforms`
- `crawl_prices_parallel` 按 `product_platforms` 分组
- 每个商品对应一个并行任务
- 每个任务只遍历该商品自己的平台列表

### 单个平台处理链路

对单个平台执行如下步骤：

1. 读取 `platform_url`
2. 使用 `PageFetchService` 通过 Playwright 打开页面并等待初步稳定
3. 获取页面最终 URL 与 HTML
4. 将 HTML 转为 Markdown
5. 调用统一 `LLMClient.generate_json(...)`
6. 输出结构化价格记录

### 输出字段

每个平台至少保留：

- `product_name`
- `platform_name`
- `platform_domain`
- `product_url`
- `raw_title`
- `spec_text`
- `currency`
- `raw_price`
- `normalized_price`
- `price_unit`
- `confidence_score`
- `source`
- `attempt_count`
- `notes`

### 失败语义

- 网页抓取失败：
  - 保留一条记录
  - 价格字段为空
  - `source = playwright_fetch_failed`
  - `notes` 写失败原因

- 网页抓取成功但未识别出价格：
  - 保留一条记录
  - 价格字段为空
  - `source = markdown_llm_unpriced`
  - `notes = 抓到网页但未识别出价格`

## 调试与详情

`crawl_prices_parallel` 的 stage `detail_json` 保留：

- 输入商品列表
- `product_platforms`
- `price_records`
- `parallel_task_count`
- `source_breakdown`

这样前端任务进度里的“查看详情”可以直接看到每个平台抓取与抽取后的结果。
