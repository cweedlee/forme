from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from config.services.original_source import TableData, TableRow, load_table
from config.services.person_rows import PersonSourceRow


@dataclass(frozen=True)
class ContractTableData:
    workbook_path: Path
    sheet_name: str
    columns: list[str]
    field_keys: list[str]
    rows: list[dict[str, Any]]
    decision_columns: list[str]
    metadata: dict[str, Any]


class ContractTable(ABC):
    """Convert parsed source rows into the view model used by contract tables."""

    engagement_type: str
    decision_columns: list[str]

    def __init__(self, workbook_path: Path, table: TableData) -> None:
        self.workbook_path = Path(workbook_path)
        self.table = table
        self.field_keys = list(table.keys)

    @classmethod
    def from_workbook(cls, workbook_path: Path) -> Self:
        return cls(
            workbook_path,
            load_table(cls.engagement_type, workbook_path),
        )

    def find_row(self, data_key: str) -> TableRow | None:
        normalized_key = str(data_key).strip()
        return next(
            (row for row in self.table.data if row.data_key == normalized_key),
            None,
        )

    def load_person(self, data_key: str) -> PersonSourceRow | None:
        row = self.find_row(data_key)
        return self.parse_person(row) if row else None

    def build(self) -> ContractTableData:
        rows: list[dict[str, Any]] = []
        for source_row in self.table.data:
            person = self.parse_person(source_row)
            if not self.has_person_identity(person):
                continue
            rows.append(self.build_view_row(source_row, person))

        return ContractTableData(
            workbook_path=self.workbook_path,
            sheet_name=self.table.sheet_name,
            columns=[self.table.keys[key] for key in self.field_keys],
            field_keys=self.field_keys,
            rows=rows,
            decision_columns=self.decision_columns,
            metadata=self.table.metadata,
        )

    def build_view_row(
        self,
        source_row: TableRow,
        person: PersonSourceRow,
    ) -> dict[str, Any]:
        return {
            "data_key": source_row.data_key,
            "source_row": source_row.source_row,
            "values": [source_row.values[key] for key in self.field_keys],
            "decisions": self.build_decisions(person),
            "person": serialize_person(person),
        }

    @abstractmethod
    def parse_person(self, row: TableRow) -> PersonSourceRow:
        """Build the engagement-specific person object from one source row."""

    @abstractmethod
    def build_decisions(self, person: PersonSourceRow) -> dict[str, str]:
        """Build engagement-specific status columns for the table."""

    @staticmethod
    def has_person_identity(person: PersonSourceRow) -> bool:
        return bool(person.key or person.name.kor or person.residence_country)


def serialize_person(person: PersonSourceRow) -> dict[str, Any]:
    return {
        "source_row": person.source_row,
        "engagement_type": person.engagement_type,
        "name": {"kor": person.name.kor, "eng": person.name.eng},
        "country_code": person.country_code,
        "residence_country": person.residence_country,
        "workplace": person.workplace,
        "key": person.key,
        "raw_by_header": person.raw_by_header,
    }
