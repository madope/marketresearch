from __future__ import annotations

from typing import Any


def _parse_price(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        value = stripped
    try:
        parsed = round(float(value), 2)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def _normalize_price_unit(value: object) -> str:
    unit = str(value or "").strip()
    if not unit:
        return "件"
    synonyms = {
        "个": "件",
        "套": "件",
        "支": "件",
    }
    return synonyms.get(unit, unit)


def _normalize_record(record: dict[str, object]) -> dict[str, object] | None:
    product_name = str(record.get("product_name", "")).strip()
    platform_name = str(record.get("platform_name", "")).strip()
    platform_domain = str(record.get("platform_domain", "")).strip().lower()
    product_url = str(record.get("product_url", "")).strip()
    if not product_name or not platform_name or not platform_domain or not product_url:
        return None

    normalized_price = _parse_price(record.get("normalized_price"))
    raw_price = _parse_price(record.get("raw_price"))
    if normalized_price is None:
        normalized_price = raw_price
    if raw_price is None:
        raw_price = normalized_price
    if normalized_price is None:
        return None

    confidence_score = max(0.0, min(round(float(record.get("confidence_score", 0.5)), 2), 1.0))
    attempt_count = max(1, int(record.get("attempt_count", 1)))

    return {
        **record,
        "product_name": product_name,
        "platform_name": platform_name,
        "platform_domain": platform_domain,
        "product_url": product_url,
        "raw_price": raw_price,
        "normalized_price": normalized_price,
        "confidence_score": confidence_score,
        "currency": str(record.get("currency", "CNY") or "CNY").upper(),
        "attempt_count": attempt_count,
        "source": str(record.get("source", "unknown")),
        "price_unit": _normalize_price_unit(record.get("price_unit")),
    }


def _record_quality_key(record: dict[str, object]) -> tuple[float, int, int]:
    source = str(record.get("source", "unknown"))
    source_penalty = 1 if source in {"playwright_fetch_failed", "markdown_llm_unpriced"} else 0
    notes_penalty = 1 if str(record.get("notes", "")).strip() else 0
    return (
        float(record.get("confidence_score", 0.0)),
        -source_penalty,
        -notes_penalty,
    )


def normalize_price_records(records: list[dict[str, object]]) -> tuple[list[dict[str, object]], dict[str, int]]:
    stats = {
        "input_count": len(records),
        "removed_missing_price_count": 0,
        "removed_invalid_format_count": 0,
        "removed_duplicate_count": 0,
        "final_count": 0,
    }

    deduped: dict[tuple[str, str, str, float], dict[str, object]] = {}
    for record in records:
        if any(
            not str(record.get(field, "")).strip()
            for field in ("product_name", "platform_name", "platform_domain", "product_url")
        ):
            stats["removed_invalid_format_count"] += 1
            continue

        parsed_raw_price = _parse_price(record.get("raw_price"))
        parsed_normalized_price = _parse_price(record.get("normalized_price"))
        if (record.get("raw_price") is not None and parsed_raw_price is None) or (
            record.get("normalized_price") is not None and parsed_normalized_price is None
        ):
            stats["removed_invalid_format_count"] += 1
            continue
        if parsed_raw_price is None and parsed_normalized_price is None:
            stats["removed_missing_price_count"] += 1
            continue

        normalized = _normalize_record(record)
        if normalized is None:
            stats["removed_invalid_format_count"] += 1
            continue

        dedupe_key = (
            str(normalized["product_name"]),
            str(normalized["platform_domain"]),
            str(normalized["product_url"]),
            float(normalized["normalized_price"]),
        )
        existing = deduped.get(dedupe_key)
        if existing is None:
            deduped[dedupe_key] = normalized
            continue
        stats["removed_duplicate_count"] += 1
        if _record_quality_key(normalized) > _record_quality_key(existing):
            deduped[dedupe_key] = normalized

    normalized_rows = list(deduped.values())
    stats["final_count"] = len(normalized_rows)
    return normalized_rows, stats
