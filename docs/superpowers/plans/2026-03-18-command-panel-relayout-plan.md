# Command Panel Relayout Plan

1. Update `frontend/src/features/research/dashboard.tsx`
   - Keep the hero title block only.
   - Move the form into the first-row right-side card.
   - Remove the old price snapshot card.

2. Update `frontend/src/features/research/dashboard.css`
   - Add a panel variant for the moved form.
   - Tighten spacing around the hero area and first-row cards.

3. Verify
   - Run `npm test -- --run tests/app.test.tsx`.
