# Remove Fake Data Fallbacks Design

## Goal

Keep workflow behavior intact while removing fake data paths from the real data pipeline.

## Scope

- Remove legacy fake price generation paths from the price crawler.
- Remove legacy `fallback_seed` / `default_seed` warnings and market-analysis data-quality hints.
- Keep non-data textual fallbacks for narrative analysis unchanged.

## Outcome

- Real platform and price acquisition failures now stay as empty/error results instead of implying synthetic data.
- The UI no longer shows stale warnings tied to removed fake data sources.
