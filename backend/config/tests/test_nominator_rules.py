from django.test import SimpleTestCase

from config.services.business_rule_config import NominatorRuleConfig, parse_business_rule_config
from config.services.person_rows import PersonName, PersonSourceRow, parse_person_source_row
from config.services.contract_generation import build_output_path, optional_clause_value, person_name_for_language
from config.services.nominator_contract import (
    PaymentClauseError,
    _payment_clauses,
    build_template_condition_flags,
    require_value,
    validate_nominator_person,
)
from project_config.nominator_rules import decide_nominator_fee


class NominatorFeeRuleTests(SimpleTestCase):
    def test_domestic_nominator_uses_domestic_fee(self):
        decision = decide_nominator_fee(
            _person(engagement_type="nominator", country_code="KR"),
            _config(domestic_fee=500000, overseas_fee=800000),
        )

        self.assertEqual(decision.status, "READY")
        self.assertEqual(decision.category, "domestic")
        self.assertEqual(decision.amount_krw, 500000)

    def test_overseas_nominator_uses_overseas_fee(self):
        decision = decide_nominator_fee(
            _person(engagement_type="노미네이터", country_code="FR"),
            _config(domestic_fee=500000, overseas_fee=800000),
        )

        self.assertEqual(decision.status, "READY")
        self.assertEqual(decision.category, "overseas")
        self.assertEqual(decision.amount_krw, 800000)

    def test_missing_country_requires_manual_review(self):
        decision = decide_nominator_fee(
            _person(engagement_type="nominator", country_code=""),
            _config(domestic_fee=500000, overseas_fee=800000),
        )

        self.assertEqual(decision.status, "MANUAL_REVIEW")
        self.assertIsNone(decision.amount_krw)

    def test_unconfigured_fee_requires_manual_review(self):
        decision = decide_nominator_fee(
            _person(engagement_type="nominator", country_code="KR"),
            _config(domestic_fee=None, overseas_fee=800000),
        )

        self.assertEqual(decision.status, "MANUAL_REVIEW")
        self.assertIsNone(decision.amount_krw)

class BusinessRuleConfigTests(SimpleTestCase):
    def test_parse_business_rule_config_keeps_user_constants_explicit(self):
        config = parse_business_rule_config(
            {
                "contract_type": {
                    "nominator": {
                        "domestic": {
                            "gross_amount": 500000,
                            "tax_type": "other-income",
                            "payment_clause_1": "계약금액 {gross_amount}원",
                        },
                        "overseas": {
                            "gross_amount": 800000,
                            "tax_type": "tax-exampt",
                            "payment_clause_1": {
                                "kor": "계약금액 {gross_amount}원",
                                "eng": "Contract amount: {gross_amount} won",
                            },
                        },
                    },
                },
                "domestic_country_codes": ["KR", "한국"],
                "tax_type": {
                    "domestic": {"other-income": 8.8},
                    "overseas": {"tax-exampt": 0},
                },
            }
        )

        self.assertEqual(config.nominator.gross_amount["domestic"], 500000)
        self.assertEqual(config.nominator.tax_type["domestic"], "other_income")
        self.assertEqual(config.nominator.tax_rates["domestic"]["other_income"], 8.8)
        self.assertEqual(
            config.nominator.payment_clauses["domestic"]["kor"]["payment_clause_1"],
            "계약금액 {gross_amount}원",
        )
        self.assertEqual(
            config.nominator.payment_clauses["overseas"]["eng"]["payment_clause_1"],
            "Contract amount: {gross_amount} won",
        )
        self.assertIn("KR", config.nominator.domestic_country_codes)


class PersonSourceRowTests(SimpleTestCase):
    def test_parse_person_source_row_maps_known_excel_headers(self):
        person = parse_person_source_row(
            source_row=3,
            headers=["key", "name_kor", "name_eng", "country_code"],
            values=["N_01", "홍길동", "Hong Gil Dong", "KR"],
            engagement_type="nominator",
        )

        self.assertEqual(person.engagement_type, "nominator")
        self.assertEqual(person.key, "N_01")
        self.assertEqual(person.name.kor, "홍길동")
        self.assertEqual(person.name.eng, "Hong Gil Dong")
        self.assertEqual(person.country_code, "KR")


class ContractLanguageTests(SimpleTestCase):
    def test_person_name_for_language_uses_english_name_when_requested(self):
        person = _person(engagement_type="nominator", country_code="KR")

        self.assertEqual(person_name_for_language(person, "kor"), "테스트")
        self.assertEqual(person_name_for_language(person, "eng"), "Test Person")

    def test_output_folder_uses_key_and_korean_name_but_file_uses_language_name(self):
        person = _person(engagement_type="nominator", country_code="KR")

        output_path = build_output_path(
            person=person,
            engagement_type="nominator",
            language="eng",
        )

        self.assertIn("[N_TEST]테스트", str(output_path.parent))
        self.assertTrue(output_path.name.startswith("Test Person_"))

    def test_missing_payment_clause_requires_error_instead_of_fallback(self):
        with self.assertRaisesRegex(PaymentClauseError, "지급 clause 설정을 찾을 수 없습니다"):
            _payment_clauses(
                {"domestic": {"kor": {}, "eng": {}}},
                "domestic",
                "kor",
                gross_amount=500000,
                tax_rate=8.8,
            )

    def test_payment_clause_renders_configured_clause(self):
        clauses = _payment_clauses(
            {
                "domestic": {
                    "kor": {
                        "payment_clause_1": "계약금액 {gross_amount}원에서 {tax_rate}%를 공제한다."
                    }
                }
            },
            "domestic",
            "kor",
            gross_amount=500000,
            tax_rate=8.8,
        )

        self.assertEqual(
            clauses["payment_clause_1"],
            "계약금액 500,000원에서 8.8%를 공제한다.",
        )

    def test_missing_optional_clause_is_marked_for_paragraph_removal(self):
        self.assertEqual(
            optional_clause_value({}, "payment_clause_2"),
            "__UNFOLDX_REMOVE_PARAGRAPH__",
        )
        self.assertEqual(
            optional_clause_value({"payment_clause_2": "추가 지급 조항"}, "payment_clause_2"),
            "추가 지급 조항",
        )

    def test_required_context_value_does_not_fallback_to_empty_value(self):
        with self.assertRaisesRegex(ValueError, "필수값이 비어 있습니다: gross_amount"):
            require_value(None, "gross_amount")

    def test_english_generation_requires_english_name(self):
        person = PersonSourceRow(
            source_row=2,
            raw_values=[],
            raw_by_header={},
            engagement_type="nominator",
            name=PersonName(kor="테스트", eng=None),
            country_code="KR",
            residence_country="KR",
            key="N_TEST",
        )

        with self.assertRaisesRegex(ValueError, "person-name-eng"):
            validate_nominator_person(person, "eng")

    def test_template_condition_flags_are_available_for_docx_if_blocks(self):
        domestic = build_template_condition_flags(category="domestic", tax_type="other_income")
        overseas = build_template_condition_flags(category="overseas", tax_type="tax_exempt")

        self.assertTrue(domestic["is_domestic"])
        self.assertFalse(domestic["is_overseas"])
        self.assertTrue(domestic["needs_withholding"])
        self.assertFalse(domestic["needs_wire_transfer_clause"])
        self.assertTrue(overseas["is_overseas"])
        self.assertTrue(overseas["is_tax_exempt"])
        self.assertTrue(overseas["needs_wire_transfer_clause"])


def _person(*, engagement_type: str, country_code: str) -> PersonSourceRow:
    return PersonSourceRow(
        source_row=2,
        raw_values=[],
        raw_by_header={},
        engagement_type=engagement_type,
        name=PersonName(kor="테스트", eng="Test Person"),
        country_code=country_code,
        residence_country=country_code or None,
        key="N_TEST",
    )


def _config(domestic_fee: int | None, overseas_fee: int | None) -> NominatorRuleConfig:
    return NominatorRuleConfig(
        gross_amount={
            "domestic": domestic_fee,
            "overseas": overseas_fee,
        },
        tax_type={
            "domestic": "other_income",
            "overseas": "tax_exempt",
        },
        payment_clauses={
            "domestic": {"kor": {}, "eng": {}},
            "overseas": {"kor": {}, "eng": {}},
        },
        domestic_country_codes={"KR", "KOR", "한국", "대한민국"},
        tax_rates={
            "domestic": {"other_income": 8.8},
            "overseas": {"tax_exempt": 0},
        },
    )
