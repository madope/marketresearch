# Analyze Prices Charts Plan

1. Add failing backend test
   - Assert `analyze_prices` preserves row URLs and emits chart datasets.

2. Update `backend/src/app/workflows/research_workflow.py`
   - Build aggregate metrics from valid prices only.
   - Add `row_count` and `charts` to `price_report`.

3. Update frontend types and UI
   - Extend `PriceReport` and `PriceReportRow`.
   - Add a `PriceChartsPanel` component based on ECharts.
   - Add a separate `价格分析图表` section and a URL column in the price table.

4. Verify
   - Run targeted backend workflow tests.
   - Run frontend dashboard tests.
