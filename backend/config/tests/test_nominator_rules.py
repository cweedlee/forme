from django.test import SimpleTestCase

from config.services.business_rule_config import NominatorRuleConfig, parse_business_rule_config
from config.services.person_rows import PersonSourceRow, parse_person_source_row
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

    def test_other_engagement_type_is_not_applicable(self):
        decision = decide_nominator_fee(
            _person(engagement_type="exhibition", country_code="KR"),
            _config(domestic_fee=500000, overseas_fee=800000),
        )

        self.assertEqual(decision.status, "NOT_APPLICABLE")


class BusinessRuleConfigTests(SimpleTestCase):
    def test_parse_business_rule_config_keeps_user_constants_explicit(self):
        config = parse_business_rule_config(
            {
                "contract-type": {
                    "nominator": {
                        "gross_amount": {"domestic": 500000, "overseas": 800000},
                    },
                },
                "domestic_country_codes": ["KR", "한국"],
            }
        )

        self.assertEqual(config.nominator.gross_amount["domestic"], 500000)
        self.assertIn("KR", config.nominator.domestic_country_codes)


class PersonSourceRowTests(SimpleTestCase):
    def test_parse_person_source_row_maps_known_excel_headers(self):
        person = parse_person_source_row(
            source_row=3,
            headers=["타입", "이름", "영문이름", "국가코드"],
            values=["노미네이터", "홍길동", "Hong Gil Dong", "KR"],
        )

        self.assertEqual(person.engagement_type, "노미네이터")
        self.assertEqual(person.name, "홍길동")
        self.assertEqual(person.english_name, "Hong Gil Dong")
        self.assertEqual(person.country_code, "KR")


def _person(*, engagement_type: str, country_code: str) -> PersonSourceRow:
    return PersonSourceRow(
        source_row=2,
        raw_values=[],
        raw_by_header={},
        engagement_type=engagement_type,
        name="테스트",
        country_code=country_code,
        residence_country=country_code or None,
    )


def _config(domestic_fee: int | None, overseas_fee: int | None) -> NominatorRuleConfig:
    return NominatorRuleConfig(
        gross_amount={
            "domestic": domestic_fee,
            "overseas": overseas_fee,
        },
        domestic_country_codes={"KR", "KOR", "한국", "대한민국"},
    )
