# LLM Platform Discovery Design

**Goal:** 将 `price_research.discover_platforms` 改成由 LLM 直接决定最终返回的网站平台列表，同时保留程序层的校验、去重和 fallback 补齐。

## Design

- `discover_platforms` 不再先做程序发现再由 LLM 排名，而是由 LLM 直接输出最终平台列表。
- LLM 输出字段包括 `platform_name`、`platform_domain`、`platform_type`、`priority`、`reason`。
- 程序层只做三件事：
  - 校验域名格式
  - 去重
  - 当 LLM 结果不足时用 fallback 平台补齐到最多 10 个

## Constraints

- 最多返回 10 个平台
- 过滤搜索引擎、论坛、纯内容站和无效域名
- 优先中国大陆电商、品牌商城和垂直交易平台

## Failure Handling

- LLM 超时或报错时，继续沿用 fallback 平台
- LLM 返回重复或无效域名时，过滤后再补 fallback
- Workflow stage 要记录 LLM 候选数、过滤数和最终保留数
