from django.test import SimpleTestCase

from project_config import nominator_rules


class NominatorFeeRuleTests(SimpleTestCase):
    def test_domestic_nominator_uses_domestic_fee(self):
        nominator_rules.NOMINATOR_FEES_KRW["domestic"] = 500000
        self.addCleanup(nominator_rules.NOMINATOR_FEES_KRW.__setitem__, "domestic", None)

        decision = nominator_rules.decide_nominator_fee(
            engagement_type="nominator",
            residence_country="KR",
        )

        self.assertEqual(decision.status, "READY")
        self.assertEqual(decision.category, "domestic")
        self.assertEqual(decision.amount_krw, 500000)

    def test_overseas_nominator_uses_overseas_fee(self):
        nominator_rules.NOMINATOR_FEES_KRW["overseas"] = 800000
        self.addCleanup(nominator_rules.NOMINATOR_FEES_KRW.__setitem__, "overseas", None)

        decision = nominator_rules.decide_nominator_fee(
            engagement_type="노미네이터",
            residence_country="FR",
        )

        self.assertEqual(decision.status, "READY")
        self.assertEqual(decision.category, "overseas")
        self.assertEqual(decision.amount_krw, 800000)

    def test_missing_country_requires_manual_review(self):
        decision = nominator_rules.decide_nominator_fee(
            engagement_type="nominator",
            residence_country="",
        )

        self.assertEqual(decision.status, "MANUAL_REVIEW")
        self.assertIsNone(decision.amount_krw)

    def test_unconfigured_fee_requires_manual_review(self):
        decision = nominator_rules.decide_nominator_fee(
            engagement_type="nominator",
            residence_country="KR",
        )

        self.assertEqual(decision.status, "MANUAL_REVIEW")
        self.assertIsNone(decision.amount_krw)

    def test_other_engagement_type_is_not_applicable(self):
        decision = nominator_rules.decide_nominator_fee(
            engagement_type="exhibition",
            residence_country="KR",
        )

        self.assertEqual(decision.status, "NOT_APPLICABLE")
