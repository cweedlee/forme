from typing import Any

from config.services.business_rule_config import load_business_rule_config
from config.services.contract_generation import optional_clause_value, person_name_for_language
from config.services.person_rows import PersonSourceRow
from project_config.nominator_rules import decide_nominator_fee


class PaymentClauseError(ValueError):
    pass


def build_nominator_context(person: PersonSourceRow, language: str = "kor") -> dict[str, Any]:
    config = load_business_rule_config()
    fee_decision = decide_nominator_fee(person, config.nominator)
    gross_amount = fee_decision.amount_krw or 0
    tax_type = config.nominator.tax_type.get(fee_decision.category or "", "tax_exempt")
    tax_rate = config.nominator.tax_rates.get(fee_decision.category or "", {}).get(tax_type or "", 0)
    tax_amount = round(gross_amount * tax_rate / 100)
    final_amount = gross_amount - tax_amount
    payment_clauses = _payment_clauses(
        config.nominator.payment_clauses,
        fee_decision.category,
        language,
        gross_amount,
        tax_rate,
    )
    return {
        "participant_name": person_name_for_language(person, language),
        "participant_name_kor": person.name.kor,
        "participant_name_eng": person.name.eng or "",
        "person_key": person.key,
        "country_code": person.country_code,
        "gross_amount": _format_number(gross_amount),
        "tax_rate": tax_rate,
        "tax_amount": _format_number(tax_amount),
        "final_amount": _format_number(final_amount),
        "payment_clause": "\n".join(payment_clauses.values()),
        "payment_clause_1": payment_clauses.get("payment_clause_1", ""),
        "payment_clause_2": optional_clause_value(payment_clauses, "payment_clause_2"),
    }


# 000,000,000 단위로 숫자 포맷팅
def _format_number(value: int) -> str:
    return f"{value:,}"


def _payment_clauses(
    clauses_by_region: dict[str, dict[str, dict[str, str]]],
    category: str | None,
    language: str,
    gross_amount: int,
    tax_rate: float,
) -> dict[str, str]:
    clauses = clauses_by_region.get(category or "", {}).get(language, {})
    rendered = {
        key: clause.format(gross_amount=_format_number(gross_amount), tax_rate=tax_rate)
        for key, clause in sorted(clauses.items())
    }
    if rendered:
        return rendered
    raise PaymentClauseError(
        f"지급 clause 설정을 찾을 수 없습니다. 확인이 필요합니다: category={category or '없음'}, language={language}"
    )
