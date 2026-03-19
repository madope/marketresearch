# Analyze Prices Charts Design

## Goal

Expand `analyze_prices` so it produces both a complete price table dataset and dedicated chart datasets for the frontend.

## Backend Changes

- Keep all cleaned price rows for table display, including `product_url`, `source`, and rows without recognized prices.
- Use only valid numeric prices for aggregate metrics such as average, min, and max.
- Add chart payloads to `price_report.charts`:
  - product vs platform grouped prices
  - platform average prices
  - product-platform coverage matrix
  - source breakdown
  - product price ranges

## Frontend Changes

- Add a standalone `价格分析图表` panel.
- Show chart data separately from the raw price table.
- Extend the price table with a `价格页 URL` column so every row can be traced back to its source page.
