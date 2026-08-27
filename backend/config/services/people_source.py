from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from django.conf import settings

from config.services.amount_decisions import decide_amounts_for_person
from config.services.business_rule_config import BusinessRuleConfig, load_business_rule_config
from config.services.person_rows import (
    PersonSourceRow,
    is_person_header_row,
    parse_person_source_row,
)


FIRST_ROW = 1
FIRST_COLUMN = 1
SHEET_DEFAULT_ENGAGEMENT_TYPES = {
    "Nominator": "nominator",
}
DECISION_COLUMNS = ["노미네이터 금액상태", "노미네이터 금액", "노미네이터 근거"]


@dataclass(frozen=True)
class WorkbookPeopleTable:
    workbook_path: Path
    sheet_name: str
    columns: list[str]
    rows: list[dict[str, Any]]
    decision_columns: list[str]


def load_people_table(
    workbook_path: Path,
    rule_config: BusinessRuleConfig | None = None,
    sheet_name: str | None = None,
) -> WorkbookPeopleTable:
    config = rule_config or load_business_rule_config()
    selected_sheet_name = sheet_name or settings.UNFOLDX_USER_DATA_SHEET
    sheet = load_people_sheet(workbook_path, selected_sheet_name)
    columns = read_table_columns(sheet)
    source_rows = read_non_empty_rows(sheet)
    rows = build_people_table_rows(source_rows, config, selected_sheet_name)

    return WorkbookPeopleTable(
        workbook_path=workbook_path,
        sheet_name=selected_sheet_name,
        columns=columns,
        rows=rows,
        decision_columns=DECISION_COLUMNS,
    )


def load_person_from_workbook(
    workbook_path: Path,
    source_row: int,
    sheet_name: str | None = None,
) -> PersonSourceRow | None:
    selected_sheet_name = sheet_name or settings.UNFOLDX_USER_DATA_SHEET
    sheet = load_people_sheet(workbook_path, selected_sheet_name)
    rows = read_non_empty_rows(sheet)
    headers: list[str] | None = None

    for row_number, values in rows:
        if is_person_header_row(values):
            headers = [str(value or "").strip() for value in values]
            continue

        if row_number == source_row and headers:
            return parse_person_source_row(
                source_row=row_number,
                headers=headers,
                values=values,
                default_engagement_type=SHEET_DEFAULT_ENGAGEMENT_TYPES.get(selected_sheet_name),
            )
    return None


def load_people_sheet(workbook_path: Path, sheet_name: str):
    if not workbook_path.exists():
        raise FileNotFoundError(f"Workbook not found: {workbook_path}")

    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    if sheet_name not in workbook.sheetnames:
        raise ValueError(f"Sheet not found: {sheet_name}")

    return workbook[sheet_name]


def read_table_columns(sheet) -> list[str]:
    return [
        get_column_letter(column)
        for column in range(FIRST_COLUMN, sheet.max_column + 1)
    ]


def read_non_empty_rows(sheet) -> list[tuple[int, list[Any]]]:
    rows: list[dict[str, Any]] = []
    for row_number in range(FIRST_ROW, sheet.max_row + 1):
        values = read_row_values(sheet, row_number)
        if _has_any_value(values):
            rows.append((row_number, values))
    return rows


def read_row_values(sheet, row_number: int) -> list[Any]:
    return [
        _clean_cell(sheet.cell(row=row_number, column=column).value)
        for column in range(FIRST_COLUMN, sheet.max_column + 1)
    ]


def build_people_table_rows(
    source_rows: list[tuple[int, list[Any]]],
    config: BusinessRuleConfig,
    sheet_name: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    headers: list[str] | None = None

    for row_number, values in source_rows:
        if is_person_header_row(values):
            headers = [str(value or "").strip() for value in values]
            rows.append(_build_preview_row(row_number, values))
            continue

        person = None
        if headers:
            person = parse_person_source_row(
                source_row=row_number,
                headers=headers,
                values=values,
                default_engagement_type=SHEET_DEFAULT_ENGAGEMENT_TYPES.get(sheet_name),
            )
        rows.append(_build_preview_row(row_number, values, person, config))

    return rows


def _clean_cell(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def _has_any_value(values: list[Any]) -> bool:
    return any(value not in (None, "") for value in values)


def _build_preview_row(
    row_number: int,
    values: list[Any],
    person: PersonSourceRow | None = None,
    config: BusinessRuleConfig | None = None,
) -> dict[str, Any]:
    row = {
        "source_row": row_number,
        "values": values,
        "decisions": {},
        "person": _serialize_person(person) if person else None,
    }
    if person and config:
        decision = decide_amounts_for_person(person, config)
        row["decisions"] = {
            "노미네이터 금액상태": decision["nominator_fee_status"],
            "노미네이터 금액": _format_krw(decision["nominator_fee_krw"]),
            "노미네이터 근거": decision["nominator_fee_reason"],
        }
    return row


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
        "name": person.name,
        "english_name": person.english_name,
        "country_code": person.country_code,
        "residence_country": person.residence_country,
        "raw_by_header": person.raw_by_header,
    }
