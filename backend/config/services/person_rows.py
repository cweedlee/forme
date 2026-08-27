from dataclasses import dataclass
from typing import Any


HEADER_ALIASES = {
    "engagement_type": {"타입", "참여유형", "계약유형"},
    "name": {"이름", "성명", "국문 이름"},
    "english_name": {"영문이름", "영문명", "영문 이름"},
    "country_code": {"국가코드"},
    "residence_country": {"거주지", "거주국", "세법상 거주국", "국가코드"},
}

REQUIRED_HEADER_MARKERS = {"국문 이름", "국가코드"}


@dataclass(frozen=True)
class PersonSourceRow:
    source_row: int
    raw_values: list[Any]
    raw_by_header: dict[str, Any]
    engagement_type: str
    name: str
    country_code: str
    english_name: str | None = None
    residence_country: str | None = None


def is_person_header_row(values: list[Any]) -> bool:
    labels = {str(value or "").strip() for value in values}
    return REQUIRED_HEADER_MARKERS.issubset(labels)


def parse_person_source_row(
    *,
    source_row: int,
    headers: list[str],
    values: list[Any],
    default_engagement_type: str | None = None,
) -> PersonSourceRow:
    raw_by_header = _row_by_header(headers, values)
    return PersonSourceRow(
        source_row=source_row,
        raw_values=values,
        raw_by_header=raw_by_header,
        engagement_type=str(
            _find_value(raw_by_header, "engagement_type") or default_engagement_type or ""
        ).strip(),
        name=str(_find_value(raw_by_header, "name") or "").strip(),
        english_name=_optional_str(_find_value(raw_by_header, "english_name")),
        country_code=str(_find_value(raw_by_header, "country_code") or "").strip(),
        residence_country=_optional_str(_find_value(raw_by_header, "residence_country")),
    )


def _row_by_header(headers: list[str], values: list[Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for index, header in enumerate(headers):
        if index < len(values):
            row[str(header or "").strip()] = values[index]
    return row


def _find_value(row: dict[str, Any], field_name: str) -> Any:
    for header, value in row.items():
        if header in HEADER_ALIASES[field_name]:
            return value
    return None


def _optional_str(value: Any) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None
