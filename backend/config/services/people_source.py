from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from config.services.amount_decisions import decide_amounts_for_source_row


SHEET_NAME = "test(해초 웹페이지용)"
FIRST_ROW = 2
FIRST_COLUMN = 2
MAPPED_HEADER_MARKERS = {"타입", "이름", "거주지"}
DECISION_COLUMNS = ["노미네이터 금액상태", "노미네이터 금액", "노미네이터 근거"]


@dataclass(frozen=True)
class WorkbookPeopleTable:
    workbook_path: Path
    sheet_name: str
    columns: list[str]
    rows: list[dict[str, Any]]
    decision_columns: list[str]


def load_people_table(workbook_path: Path) -> WorkbookPeopleTable:
    if not workbook_path.exists():
        raise FileNotFoundError(f"Workbook not found: {workbook_path}")

    workbook = load_workbook(workbook_path, read_only=True, data_only=True)
    if SHEET_NAME not in workbook.sheetnames:
        raise ValueError(f"Sheet not found: {SHEET_NAME}")

    sheet = workbook[SHEET_NAME]
    columns = [
        get_column_letter(column)
        for column in range(FIRST_COLUMN, sheet.max_column + 1)
    ]
    rows: list[dict[str, Any]] = []

    mapped_headers: list[str] | None = None

    for row_number in range(FIRST_ROW, sheet.max_row + 1):
        values = [
            _clean_cell(sheet.cell(row=row_number, column=column).value)
            for column in range(FIRST_COLUMN, sheet.max_column + 1)
        ]
        if not any(value not in (None, "") for value in values):
            continue

        if _is_mapped_header_row(values):
            mapped_headers = [str(value or "").strip() for value in values]

        rows.append(_build_source_row(row_number, values, mapped_headers))

    return WorkbookPeopleTable(
        workbook_path=workbook_path,
        sheet_name=SHEET_NAME,
        columns=columns,
        rows=rows,
        decision_columns=DECISION_COLUMNS,
    )


def _clean_cell(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def _is_mapped_header_row(values: list[Any]) -> bool:
    labels = {str(value or "").strip() for value in values}
    return MAPPED_HEADER_MARKERS.issubset(labels)


def _build_source_row(
    row_number: int,
    values: list[Any],
    mapped_headers: list[str] | None,
) -> dict[str, Any]:
    row = {
        "source_row": row_number,
        "values": values,
        "decisions": {},
    }
    if mapped_headers and not _is_mapped_header_row(values):
        decision = decide_amounts_for_source_row(mapped_headers, values)
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
