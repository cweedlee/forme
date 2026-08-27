from config.services.business_rule_config import BusinessRuleConfig
from config.services.person_rows import PersonSourceRow
from project_config.nominator_rules import NominatorFeeDecision, decide_nominator_fee


def decide_amounts_for_person(person: PersonSourceRow, config: BusinessRuleConfig) -> dict[str, object]:
    decision = decide_nominator_fee(person, config.nominator)
    return _serialize_nominator_decision(decision)


def _serialize_nominator_decision(decision: NominatorFeeDecision) -> dict[str, object]:
    return {
        "nominator_fee_status": decision.status,
        "nominator_fee_krw": decision.amount_krw,
        "nominator_fee_category": decision.category,
        "nominator_fee_reason": decision.reason,
    }
