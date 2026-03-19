# Remove Fake Data Fallbacks Plan

1. Add failing workflow tests
   - Verify `analyze_prices` no longer emits legacy `fallback_seed/default_seed` warnings.
   - Verify `build_from_zero_plan` no longer injects fallback-platform data quality hints.

2. Remove legacy fake-data code
   - Delete unused default fake-price logic from `backend/src/app/services/crawl_service.py`.
   - Remove legacy fake-data warning branches from `backend/src/app/workflows/research_workflow.py`.

3. Verify
   - Run targeted workflow tests.
   - Run backend workflow/service/api regression tests.
