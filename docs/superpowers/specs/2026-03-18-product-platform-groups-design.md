# Product Platform Groups Design

## 目标

将 `discover_platforms` 从“所有商品共享一组平台”改成“每个商品独立发现平台”。

## 行为

- 对 `products` 中的每个商品分别执行 `web_search`
- 每个商品最多搜索 3 轮
- 每个商品目标收集 10 个真实平台
- 3 轮后不足 10 个时，只返回真实搜到的数据，不补假数据，不让任务失败

## 数据结构

工作流状态新增 `product_platforms`：

```json
[
  {
    "product_name": "电动牙刷 标准款",
    "platforms": [],
    "metrics": {
      "candidate_count": 12,
      "invalid_count": 2,
      "final_count": 10
    }
  }
]
```

同时保留扁平 `platforms`，作为全局汇总视图，方便现有后续逻辑兼容。

## 抓取链路

- `crawl_prices_parallel` 优先读取 `product_platforms`
- 每个商品只在自己的平台列表上抓取价格
- 不再把所有商品与同一组平台做笛卡尔积

## 前端/详情

- `discover_platforms` 的 `detail_json` 中保留 `product_platforms`
- 任务进度展开详情时，可以看到每个商品对应的平台结果
