# Remove LLM Review Price Rows Plan

1. Update `backend/src/app/workflows/research_workflow.py`
   - Delete `_llm_review_price_rows`.
   - Make `crawl_prices_parallel` use `raw_price_records` directly.

2. Update `backend/tests/test_workflow.py`
   - Remove direct tests for `_llm_review_price_rows`.
   - Assert `crawl_prices_parallel` no longer emits the removed stage.

3. Verify
   - Run `pytest tests/test_workflow.py`.
