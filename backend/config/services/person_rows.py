from dataclasses import dataclass
from typing import Any


DISPLAY_LABELS = {
    "식별자": "key",
    "구분": "key",
    "국문 이름": "person_name_kor",
    "국문 성명": "person_name_kor",
    "이름": "person_name_kor",
    "성명": "person_name_kor",
    "영문 이름": "person_name_eng",
    "영문 성명": "person_name_eng",
    "영문이름": "person_name_eng",
    "영문명": "person_name_eng",
    "국가코드": "country_code",
    "거주지": "residence_country",
    "거주국": "residence_country",
    "세법상 거주국": "residence_country",
    "국가": "residence_country",
    "업무수행장소": "workplace",
    "수행장소": "workplace",
    "key": "key",
    "person_key": "key",
    "kor_key": "key",
    "person_name_kor": "person_name_kor",
    "person-name-kor": "person_name_kor",
    "name_kor": "person_name_kor",
    "person_name_eng": "person_name_eng",
    "person-name-eng": "person_name_eng",
    "name_eng": "person_name_eng",
    "residence_country": "residence_country",
    "residence-country": "residence_country",
    "country_code": "country_code",
    "workplace": "workplace",
    "work_location": "workplace",
    "work-location": "workplace",
}

REQUIRED_FIELDS = {"key", "person_name_kor", "person_name_eng", "residence_country"}


@dataclass(frozen=True)
class PersonName:
    kor: str
    eng: str | None = None


@dataclass(frozen=True)
class PersonSourceRow:
    source_row: int
    raw_values: list[Any]
    raw_by_header: dict[str, Any]
    engagement_type: str
    key: str
    name: PersonName
    country_code: str
    residence_country: str | None = None
    workplace: str | None = None


def is_person_code_header_row(values: list[Any]) -> bool:
    seen_fields = {
        _field_key_from_header(value)
        for value in values
        if _field_key_from_header(value) is not None
    }
    return REQUIRED_FIELDS.issubset(seen_fields)


def parse_person_source_row(
    *,
    source_row: int,
    headers: list[str],
    values: list[Any],
    engagement_type: str,
) -> PersonSourceRow:
    raw_by_header = _row_by_header(headers, values)
    return PersonSourceRow(
        source_row=source_row,
        raw_values=values,
        raw_by_header=raw_by_header,
        engagement_type=engagement_type,
        key=str(_find_value(raw_by_header, "key") or "").strip(),
        name=PersonName(
            kor=str(_find_value(raw_by_header, "person_name_kor") or "").strip(),
            eng=_optional_str(_find_value(raw_by_header, "person_name_eng")),
        ),
        country_code=str(_find_value(raw_by_header, "country_code") or "").strip(),
        residence_country=_optional_str(_find_value(raw_by_header, "residence_country")),
        workplace=_optional_str(_find_value(raw_by_header, "workplace")),
    )


def _row_by_header(headers: list[str], values: list[Any]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for index, header in enumerate(headers):
        if index < len(values):
            row[str(header or "").strip()] = values[index]
    return row


def _find_value(row: dict[str, Any], field_name: str) -> Any:
    for header, value in row.items():
        if _field_key_from_header(header) == field_name:
            return value
    return None


def field_key_from_header(header: Any) -> str | None:
    normalized = _normalize_header(header)
    if normalized in DISPLAY_LABELS:
        return DISPLAY_LABELS[normalized]
    return None


def _field_key_from_header(header: Any) -> str | None:
    return field_key_from_header(header)


def _normalize_header(value: str) -> str:
    return str(value or "").strip().replace("-", "_").lower()


def _optional_str(value: Any) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None
