from dataclasses import dataclass
from typing import Any


HEADER_ALIASES = {
    "key": {"key", "person_key", "kor_key", "KOR_KEY", "식별자", "구분"},
    "name_kor": {"name_kor", "person_name_kor", "국문 이름", "국문 성명", "이름", "성명"},
    "name_eng": {"name_eng", "person_name_eng", "english_name", "영문 이름", "영문 성명", "영문이름", "영문명"},
    "country_code": {"country_code", "국가코드"},
    "residence_country": {"residence_country", "거주지", "거주국", "세법상 거주국", "국가"},
    "workplace": {"workplace", "work_location", "업무수행장소", "수행장소"},
}

REQUIRED_FIELDS = {"key", "name_kor", "name_eng", "residence_country"}


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
    labels = {normalize_header(str(value or "").strip()) for value in values}
    return all(
        labels & {normalize_header(alias) for alias in HEADER_ALIASES[field_name]}
        for field_name in REQUIRED_FIELDS
    )


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
            kor=str(_find_value(raw_by_header, "name_kor") or "").strip(),
            eng=_optional_str(_find_value(raw_by_header, "name_eng")),
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
    return find_header_value(row, HEADER_ALIASES[field_name])


def normalize_header(value: Any) -> str:
    return str(value or "").strip().replace("-", "_").lower()


def find_header_value(row: dict[str, Any], aliases: set[str]) -> Any:
    normalized_aliases = {normalize_header(alias) for alias in aliases}
    for header, value in row.items():
        if normalize_header(header) in normalized_aliases:
            return value
    return None


def _optional_str(value: Any) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None
