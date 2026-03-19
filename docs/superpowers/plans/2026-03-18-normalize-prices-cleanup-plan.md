# Normalize Prices Cleanup Plan

1. Update `backend/tests/test_services.py`
   - Add failing tests for invalid-row filtering, unit normalization, and deduplication.

2. Update `backend/tests/test_workflow.py`
   - Add a failing test asserting `normalize_prices` reports cleanup stats.

3. Update `backend/src/app/services/normalize_service.py`
   - Parse numeric values safely.
   - Filter invalid rows.
   - Normalize units and core fields.
   - Deduplicate and return stats.

4. Update `backend/src/app/workflows/research_workflow.py`
   - Use cleanup stats in `normalize_prices` stage message and detail.

5. Verify
   - Run targeted normalize tests.
   - Run backend workflow/service/api regression tests.
