from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config.services.original_source import TableData, load_table
from config.services.person_rows import (
    PersonSourceRow,
    parse_person_source_row,
)


ENGAGEMENT_TYPE = "nominator"
DECISION_COLUMNS = ["계약서 상태", "검증 메시지"]
REQUIRED_CONTEXT_FIELDS = {
    "key": {"식별자", "key"},
    "person_name_kor": {"person_name_kor", "국문 성명", "국문 이름", "성명"},
    "tax_residence": {"residence_country", "세법상 거주국", "국가"},
    "work_location": {"workplace", "work_location", "업무수행장소"},
    "gross_amount": {"gross_amount", "계약금액"},
    "income_type": {"income_type", "소득종류"},
    "tax_rate": {"tax_rate", "원천징수율"},
    "tax_amount": {"tax_amount", "원천징수세액(KRW)"},
    "final_amount": {"final_amount", "최종 지급액"},
}


@dataclass(frozen=True)
class NominatorWorkbookTable:
    workbook_path: Path
    sheet_name: str
    columns: list[str]
    field_keys: list[str]
    rows: list[dict[str, Any]]
    decision_columns: list[str]
    metadata: dict[str, Any]


def load_nominator_table(
    workbook_path: Path,
) -> NominatorWorkbookTable:
    table = load_table(ENGAGEMENT_TYPE, workbook_path)
    field_keys = list(table.keys)
    rows = build_nominator_table_rows(table, field_keys)

    return NominatorWorkbookTable(
        workbook_path=workbook_path,
        sheet_name=table.sheet_name,
        columns=[table.keys[key] for key in field_keys],
        field_keys=field_keys,
        rows=rows,
        decision_columns=DECISION_COLUMNS,
        metadata=table.metadata,
    )


def load_nominator_person_from_workbook(
    workbook_path: Path,
    data_key: str,
) -> PersonSourceRow | None:
    table = load_table(ENGAGEMENT_TYPE, workbook_path)
    headers = list(table.keys)
    for row in table.data:
        if row.data_key == data_key:
            return _parse_person(row.source_row, headers, row.values)
    return None


def build_nominator_table_rows(
    table: TableData,
    field_keys: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in table.data:
        person = _parse_person(row.source_row, field_keys, row.values)
        if not _has_person_identity(person):
            continue
        rows.append(
            _build_preview_row(
                row.source_row,
                [row.values[key] for key in field_keys],
                person,
                data_key=row.data_key,
            )
        )

    return rows


def _has_any_value(values: list[Any]) -> bool:
    return any(value not in (None, "") for value in values)


def _has_person_identity(person: PersonSourceRow) -> bool:
    return bool(person.key or person.name.kor or person.residence_country)


def _normalize_header(value: Any) -> str:
    return str(value or "").strip().replace("-", "_").lower()


def _build_preview_row(
    row_number: int,
    values: list[Any],
    person: PersonSourceRow | None = None,
    data_key: str = "",
) -> dict[str, Any]:
    row = {
        "data_key": data_key,
        "source_row": row_number,
        "values": values,
        "decisions": {},
        "person": _serialize_person(person) if person else None,
    }
    if person:
        row["decisions"] = build_row_decisions(person)
    return row


def _parse_person(source_row: int, headers: list[str], row: dict[str, Any]) -> PersonSourceRow:
    return parse_person_source_row(
        source_row=source_row,
        headers=headers,
        values=[row[header] for header in headers],
        engagement_type=ENGAGEMENT_TYPE,
    )


def build_row_decisions(person: PersonSourceRow) -> dict[str, str]:
    missing = missing_required_context_fields(person)
    if missing:
        return {
            "계약서 상태": "ERROR",
            "검증 메시지": "필수값 누락: " + ", ".join(missing),
        }
    return {
        "계약서 상태": "READY",
        "검증 메시지": "Excel 계산값 사용",
    }


def missing_required_context_fields(person: PersonSourceRow) -> list[str]:
    missing = []
    for field_name, aliases in REQUIRED_CONTEXT_FIELDS.items():
        if _mapped_value(person.raw_by_header, aliases) in (None, ""):
            missing.append(field_name)
    return missing


def _mapped_value(row: dict[str, Any], aliases: set[str]) -> Any:
    normalized_aliases = {_normalize_header(alias) for alias in aliases}
    for header, value in row.items():
        if _normalize_header(header) in normalized_aliases:
            return value
    return None


def _format_krw(value: Any) -> str:
    if value is None:
        return ""
    return f"{value:,}원"


def _serialize_person(person: PersonSourceRow | None) -> dict[str, Any] | None:
    if not person:
        return None
    return {
        "source_row": person.source_row,
        "engagement_type": person.engagement_type,
        "name": {
            "kor": person.name.kor,
            "eng": person.name.eng,
        },
        "country_code": person.country_code,
        "residence_country": person.residence_country,
        "workplace": person.workplace,
        "key": person.key,
        "raw_by_header": person.raw_by_header,
    }
