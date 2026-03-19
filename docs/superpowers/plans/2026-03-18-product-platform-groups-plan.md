# Product Platform Groups Plan

1. 为 `discover_platforms` 增加按商品搜索的平台发现逻辑
   - 单商品独立搜索
   - 商品级任务并行执行
   - 3 轮内尽量收集 10 个真实平台
   - 输出 `product_platforms` 和汇总 `platforms`

2. 调整价格抓取
   - `PriceCrawlerService.crawl_prices(...)` 支持 `product_platforms`
   - `crawl_prices_parallel` 优先按商品自己的平台集合抓取

3. 调整步骤详情
   - `discover_platforms` 的 `detail_json` 带上 `product_platforms`
   - `crawl_prices_parallel` 的 `detail_json` 带上 `product_platforms`

4. 测试与验证
   - `discover_platforms` 测试覆盖多商品、多轮搜索、不足 10 的场景
   - `crawl_prices_parallel` 测试覆盖按商品平台抓取
