from django.test import SimpleTestCase

from config.services.contract_generation import build_output_path, optional_clause_value, person_name_for_language
from config.services.country_codes import parse_country_code_rows
from config.services.nominator_contract import (
    build_template_condition_flags,
    read_nominator_source_values,
    require_value,
    validate_nominator_person,
)
from config.services.nominator_source import build_row_decisions
from config.services.person_rows import PersonName, PersonSourceRow, parse_person_source_row


class PersonSourceRowTests(SimpleTestCase):
    def test_parse_person_source_row_maps_current_excel_headers(self):
        person = parse_person_source_row(
            source_row=10,
            headers=["식별자", "국문 성명", "영문 성명", "세법상 거주국"],
            values=["N01", "민소연", "Soyeon Min", "대한민국"],
            engagement_type="nominator",
        )

        self.assertEqual(person.engagement_type, "nominator")
        self.assertEqual(person.key, "N01")
        self.assertEqual(person.name.kor, "민소연")
        self.assertEqual(person.name.eng, "Soyeon Min")
        self.assertEqual(person.residence_country, "대한민국")
        self.assertEqual(person.country_code, "")

    def test_parse_person_source_row_maps_code_style_headers(self):
        person = parse_person_source_row(
            source_row=10,
            headers=["key", "person-name-kor", "person-name-eng", "residence-country"],
            values=["N01", "민소연", "Soyeon Min", "대한민국"],
            engagement_type="nominator",
        )

        self.assertEqual(person.key, "N01")
        self.assertEqual(person.name.kor, "민소연")
        self.assertEqual(person.name.eng, "Soyeon Min")
        self.assertEqual(person.residence_country, "대한민국")

    def test_read_nominator_source_values_accepts_code_style_headers(self):
        person = parse_person_source_row(
            source_row=10,
            headers=[
                "key",
                "person-name-kor",
                "person-name-eng",
                "residence-country",
                "work-location",
                "gross-amount",
                "income-type",
                "tax-rate",
                "tax-amount",
                "final-amount",
                "contract-date",
            ],
            values=[
                "N01",
                "민소연",
                "Soyeon Min",
                "대한민국",
                "대한민국",
                500000,
                "기타소득",
                0.088,
                44000,
                456000,
                "2026-01-01",
            ],
            engagement_type="nominator",
        )

        source_values = read_nominator_source_values(person)

        self.assertEqual(source_values["contract_date"], "2026-01-01")
        self.assertEqual(source_values["tax_residence"], "대한민국")
        self.assertEqual(source_values["tax_rate"], 0.088)


class NominatorContractContextTests(SimpleTestCase):
    def test_source_values_are_read_from_excel_row_headers(self):
        values = read_nominator_source_values(_person())

        self.assertEqual(values["contract_date"], "2026년 0월 00일")
        self.assertEqual(values["tax_residence"], "대한민국")
        self.assertEqual(values["workplace"], "대한민국")
        self.assertEqual(values["gross_amount"], 500000)
        self.assertEqual(values["income_type"], "기타소득")
        self.assertEqual(values["tax_rate"], 0.088)
        self.assertEqual(values["tax_amount"], 44000)
        self.assertEqual(values["final_amount"], 456000)

    def test_row_decision_uses_excel_values_not_rules(self):
        decision = build_row_decisions(_person())

        self.assertEqual(decision["계약서 상태"], "READY")
        self.assertEqual(decision["검증 메시지"], "Excel 계산값 사용")

    def test_country_code_rows_are_parsed_from_workbook_sheet(self):
        country_codes = parse_country_code_rows(
            [
                ["국가", "국가코드"],
                ["대한민국", "KR"],
                ["캐나다", "CA"],
            ]
        )

        self.assertEqual(country_codes["대한민국"], "KR")
        self.assertEqual(country_codes["캐나다"], "CA")

    def test_country_code_rows_accept_current_code_headers(self):
        country_codes = parse_country_code_rows(
            [
                ["residence_country", "country_code"],
                ["대한민국", "KR"],
                ["일본", "JP"],
            ]
        )

        self.assertEqual(country_codes["대한민국"], "KR")
        self.assertEqual(country_codes["일본"], "JP")

    def test_missing_required_context_value_is_error(self):
        person = _person(raw_by_header={"식별자": "N01"})

        decision = build_row_decisions(person)

        self.assertEqual(decision["계약서 상태"], "ERROR")
        self.assertIn("gross_amount", decision["검증 메시지"])

    def test_required_context_value_does_not_fallback_to_empty_value(self):
        with self.assertRaisesRegex(ValueError, "필수값이 비어 있습니다: gross_amount"):
            require_value(None, "gross_amount")

    def test_english_generation_requires_english_name(self):
        person = _person(name=PersonName(kor="테스트", eng=None))

        with self.assertRaisesRegex(ValueError, "person-name-eng"):
            validate_nominator_person(person, "eng")

    def test_template_condition_flags_are_available_for_docx_if_blocks(self):
        domestic = build_template_condition_flags(category="domestic", tax_type="기타소득")
        overseas = build_template_condition_flags(category="overseas", tax_type="해당없음")

        self.assertTrue(domestic["is_domestic"])
        self.assertFalse(domestic["is_overseas"])
        self.assertTrue(domestic["needs_withholding"])
        self.assertFalse(domestic["needs_wire_transfer_clause"])
        self.assertTrue(overseas["is_overseas"])
        self.assertTrue(overseas["is_tax_exempt"])
        self.assertTrue(overseas["needs_wire_transfer_clause"])


class ContractLanguageTests(SimpleTestCase):
    def test_person_name_for_language_uses_english_name_when_requested(self):
        person = _person()

        self.assertEqual(person_name_for_language(person, "kor"), "민소연")
        self.assertEqual(person_name_for_language(person, "eng"), "Soyeon Min")

    def test_output_folder_uses_key_and_korean_name_but_file_uses_language_name(self):
        output_path = build_output_path(
            person=_person(),
            engagement_type="nominator",
            language="eng",
        )

        self.assertIn("[N01]민소연", str(output_path.parent))
        self.assertTrue(output_path.name.startswith("Soyeon Min_"))

    def test_missing_optional_clause_is_marked_for_paragraph_removal(self):
        self.assertEqual(
            optional_clause_value({}, "payment_clause_2"),
            "__UNFOLDX_REMOVE_PARAGRAPH__",
        )
        self.assertEqual(
            optional_clause_value({"payment_clause_2": "추가 지급 조항"}, "payment_clause_2"),
            "추가 지급 조항",
        )


def _person(
    *,
    name: PersonName | None = None,
    raw_by_header: dict[str, object] | None = None,
) -> PersonSourceRow:
    row = raw_by_header or {
        "식별자": "N01",
        "국문 성명": "민소연",
        "영문 성명": "Soyeon Min",
        "계약체결일": "2026년 0월 00일",
        "세법상 거주국": "대한민국",
        "업무수행장소": "대한민국",
        "계약금액": 500000,
        "소득종류": "기타소득",
        "원천징수율": 0.088,
        "원천징수세액(KRW)": 44000,
        "최종 지급액": 456000,
    }
    return PersonSourceRow(
        source_row=10,
        raw_values=[],
        raw_by_header=row,
        engagement_type="nominator",
        key=str(row.get("식별자") or "N01"),
        name=name or PersonName(kor=str(row.get("국문 성명") or "민소연"), eng=str(row.get("영문 성명") or "Soyeon Min")),
        country_code="",
        residence_country=str(row.get("세법상 거주국") or "대한민국"),
        workplace=str(row.get("업무수행장소") or "대한민국"),
    )
