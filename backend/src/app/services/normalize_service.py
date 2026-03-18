from __future__ import annotations


def normalize_price_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for record in records:
        normalized.append(
            {
                **record,
                "raw_price": round(float(record["raw_price"]), 2) if record.get("raw_price") is not None else None,
                "normalized_price": round(float(record["normalized_price"]), 2)
                if record.get("normalized_price") is not None
                else None,
                "confidence_score": round(float(record.get("confidence_score", 0.5)), 2),
                "currency": str(record.get("currency", "CNY")).upper(),
                "attempt_count": int(record.get("attempt_count", 1)),
                "source": str(record.get("source", "unknown")),
            }
        )
    return normalized
