# Normalize Prices Cleanup Design

## Goal

Make `normalize_prices` a deterministic cleanup step for price records instead of a light formatting pass.

## Rules

- Drop rows with no usable price.
- Drop rows with invalid numeric price formats.
- Drop rows with missing required identifiers such as product, platform, domain, or URL.
- Normalize currency, numeric fields, attempt count, and price units.
- Deduplicate rows by product, platform domain, product URL, and normalized price.
- Prefer the more complete row when duplicates collide.

## Output

- Return cleaned `price_records`.
- Attach cleanup statistics to the `normalize_prices` stage detail.
- Surface removal and dedup counts in the stage message.
