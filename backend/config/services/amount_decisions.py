from typing import Any

from project_config.nominator_rules import NominatorFeeDecision, decide_nominator_fee


HEADER_ALIASES = {
    "engagement_type": {"타입", "참여유형", "계약유형"},
    "residence_country": {"거주지", "거주국", "세법상 거주국"},
}


def decide_amounts_for_source_row(headers: list[str], values: list[Any]) -> dict[str, Any]:
    row = _row_by_header(headers, values)
    decision = decide_nominator_fee(
        engagement_type=_find_value(row, "engagement_type"),
        residence_country=_find_value(row, "residence_country"),
    )
    return _serialize_nominator_decision(decision)


def _row_by_header(headers: list[str], values: list[Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for index, header in enumerate(headers):
        if index < len(values):
            row[str(header or "").strip()] = values[index]
    return row


def _find_value(row: dict[str, Any], field_name: str) -> Any:
    aliases = HEADER_ALIASES[field_name]
    for header, value in row.items():
        if header in aliases:
            return value
    return None


def _serialize_nominator_decision(decision: NominatorFeeDecision) -> dict[str, Any]:
    return {
        "nominator_fee_status": decision.status,
        "nominator_fee_krw": decision.amount_krw,
        "nominator_fee_category": decision.category,
        "nominator_fee_reason": decision.reason,
    }
