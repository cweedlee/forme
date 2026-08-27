from typing import Any

from config.services.business_rule_config import load_business_rule_config
from config.services.contract_generation import optional_clause_value, person_name_for_language
from config.services.person_rows import PersonSourceRow
from project_config.nominator_rules import decide_nominator_fee


class PaymentClauseError(ValueError):
    pass


def build_nominator_context(person: PersonSourceRow, language: str = "kor") -> dict[str, Any]:
    validate_nominator_person(person, language)
    config = load_business_rule_config()
    fee_decision = decide_nominator_fee(person, config.nominator)
    if fee_decision.status != "READY":
        raise ValueError(f"노미네이터 금액을 확정할 수 없습니다: {fee_decision.reason}")

    category = require_value(fee_decision.category, "nominator category")
    gross_amount = require_value(fee_decision.amount_krw, "gross_amount")
    tax_type = require_value(config.nominator.tax_type.get(category), f"tax_type.{category}")
    tax_rate = require_value(
        config.nominator.tax_rates.get(category, {}).get(tax_type),
        f"tax_rate.{category}.{tax_type}",
    )
    template_flags = build_template_condition_flags(category=category, tax_type=tax_type)
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
        "participant_name_eng": require_value(person.name.eng, "person-name-eng"),
        "person_key": person.key,
        "country_code": person.country_code,
        "tax_type": tax_type,
        **template_flags,
        "gross_amount": _format_number(gross_amount),
        "tax_rate": tax_rate,
        "tax_amount": _format_number(tax_amount),
        "final_amount": _format_number(final_amount),
        "payment_clause": "\n".join(payment_clauses.values()),
        "payment_clause_1": require_value(payment_clauses.get("payment_clause_1"), "payment_clause_1"),
        "payment_clause_2": optional_clause_value(payment_clauses, "payment_clause_2"),
    }


def build_template_condition_flags(*, category: str, tax_type: str) -> dict[str, bool]:
    return {
        "is_domestic": category == "domestic",
        "is_overseas": category == "overseas",
        "needs_withholding": tax_type != "tax_exempt",
        "is_tax_exempt": tax_type == "tax_exempt",
        "needs_wire_transfer_clause": category == "overseas",
    }


def validate_nominator_person(person: PersonSourceRow, language: str) -> None:
    require_value(person.key, "person-key")
    require_value(person.name.kor, "person-name-kor")
    if language == "eng":
        require_value(person.name.eng, "person-name-eng")
    require_value(person.country_code, "country-code")


def require_value(value: Any, field_name: str):
    if value in (None, ""):
        raise ValueError(f"필수값이 비어 있습니다: {field_name}")
    return value


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
    category = require_value(category, "payment_clause category")
    clauses = clauses_by_region.get(category, {}).get(language, {})
    rendered = {
        key: clause.format(gross_amount=_format_number(gross_amount), tax_rate=tax_rate)
        for key, clause in sorted(clauses.items())
    }
    if rendered:
        return rendered
    raise PaymentClauseError(
        f"지급 clause 설정을 찾을 수 없습니다. 확인이 필요합니다: category={category or '없음'}, language={language}"
    )
