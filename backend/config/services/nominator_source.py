from config.services.contract_table import ContractTable
from config.services.original_source import TableRow
from config.services.person_rows import PersonSourceRow, find_header_value, parse_person_source_row


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


class NominatorContractTable(ContractTable):
    engagement_type = ENGAGEMENT_TYPE
    decision_columns = DECISION_COLUMNS

    def parse_person(self, row: TableRow) -> PersonSourceRow:
        return parse_person_source_row(
            source_row=row.source_row,
            headers=self.field_keys,
            values=[row.values[key] for key in self.field_keys],
            engagement_type=self.engagement_type,
        )

    def build_decisions(self, person: PersonSourceRow) -> dict[str, str]:
        missing = self._missing_required_context_fields(person)
        if missing:
            return {
                "계약서 상태": "ERROR",
                "검증 메시지": "필수값 누락: " + ", ".join(missing),
            }
        return {
            "계약서 상태": "READY",
            "검증 메시지": "Excel 계산값 사용",
        }

    @staticmethod
    def _missing_required_context_fields(person: PersonSourceRow) -> list[str]:
        return [
            field_name
            for field_name, aliases in REQUIRED_CONTEXT_FIELDS.items()
            if find_header_value(person.raw_by_header, aliases) in (None, "")
        ]
