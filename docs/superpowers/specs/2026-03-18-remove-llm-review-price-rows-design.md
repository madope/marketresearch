# Remove LLM Review Price Rows Design

## Goal

Remove the secondary `_llm_review_price_rows` post-processing step from the price crawling workflow.

## Rationale

- Price extraction already happens during the Playwright -> Markdown -> LLM pipeline.
- The extra review step only touched a small preview subset and added another LLM call.
- Removing it reduces latency, failure points, and stage noise.

## Result

- `crawl_prices_parallel` now returns raw crawl results directly.
- The workflow no longer emits an `llm_review_price_rows` stage.
