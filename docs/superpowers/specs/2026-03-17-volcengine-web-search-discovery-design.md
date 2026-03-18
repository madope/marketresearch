# Volcengine Web Search Discovery Design

**Goal:** 将 `discover_platforms` 改成优先使用火山方舟原生 `web_search` 实时搜索平台，并返回平台名称、主域名、平台简介以及能显示商品价格的真实页面 URL；若不足 10 个平台则继续搜索，最多 3 轮，不补假数据；`crawl_prices_parallel` 直接消费 `platform_url` 抓取价格。

## Design

- 在统一 LLM 客户端层新增 `search_web(prompt, fallback)` 接口。
- `VolcengineArkClient.search_web` 使用官方 `Responses API` 和 `tools=[{"type":"web_search"}]`。
- `discover_platforms` 改为优先消费 `search_web` 返回的平台列表，而不是只靠模型经验推断。
- 每个平台保留 `search_evidence`：
  - `query`
  - `title`
  - `url`
  - `snippet`
- 每个平台新增：
  - `platform_url`
  - `platform_summary`
- `discover_platforms` 使用最多 3 轮 web search：
  - 每轮去重、校验域名和 URL
  - 如果不足 10 个，则带上已排除域名发起下一轮
  - 若 3 轮后仍不足 10 个，只返回真实搜索到的结果
- `crawl_prices_parallel` 不再优先拼接伪搜索地址，而是优先使用 `platform_url` 抓取真实商品页。

## Provider Behavior

- `volcengine`: 使用原生 web search
- `kimi`: 当前未接官方原生 web search，明确返回 fallback

## Failure Handling

- web search 超时或异常时，写 stage 提示，并保留此前已搜到的真实结果
- 返回无效或重复域名时，程序过滤，但不补 fake/fallback 平台
- 若 3 轮结束后仍不足 10 个平台，正常返回现有真实结果
- 若真实商品页抓取失败，再回退到 provider/default seed
