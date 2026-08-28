from typing import Any

from config.services.contract_generation import optional_clause_value, person_name_for_language
from config.services.country_codes import resolve_country_code
from config.services.person_rows import PersonSourceRow


NOMINATOR_CONTEXT_FIELDS = {
    "contract_date": {"계약체결일"},
    "tax_residence": {"세법상 거주국", "국가"},
    "workplace": {"업무수행장소"},
    "gross_amount": {"계약금액"},
    "income_type": {"소득종류"},
    "tax_rate": {"원천징수율"},
    "tax_amount": {"원천징수세액(KRW)"},
    "final_amount": {"최종 지급액"},
}


def build_nominator_context(person: PersonSourceRow, language: str = "kor") -> dict[str, Any]:
    validate_nominator_person(person, language)
    source_values = read_nominator_source_values(person)
    gross_amount = source_values["gross_amount"]
    tax_rate = source_values["tax_rate"]
    tax_amount = source_values["tax_amount"]
    final_amount = source_values["final_amount"]
    tax_type = source_values["income_type"]
    residence_country = source_values["tax_residence"]
    workplace = source_values["workplace"]
    country_code = resolve_country_code(residence_country)
    category = "domestic" if workplace == "대한민국" else "overseas"
    template_flags = build_template_condition_flags(category=category, tax_type=tax_type)
    return {
        "participant_name": person_name_for_language(person, language),
        "person_name_kor": person.name.kor,
        "person_name_eng": person.name.eng or "",
        "participant_name_kor": person.name.kor,
        "participant_name_eng": person.name.eng or "",
        "person_key": person.key,
        "country_code": country_code,
        "contract_date": source_values["contract_date"],
        "contract_sign_date": source_values["contract_date"],
        "residence_country": residence_country,
        "tax_residence": residence_country,
        "workplace": workplace,
        "work_location": workplace,
        "income_type": source_values["income_type"],
        "tax_type": tax_type,
        **template_flags,
        "gross_amount": _format_number(gross_amount),
        "tax_rate": _format_rate(tax_rate),
        "tax_amount": _format_number(tax_amount),
        "final_amount": _format_number(final_amount),
        "payment_clause": "",
        "payment_clause_1": "",
        "payment_clause_2": optional_clause_value({}, "payment_clause_2"),
    }


def build_template_condition_flags(*, category: str, tax_type: str) -> dict[str, bool]:
    is_tax_exempt = tax_type in {"해당없음", "tax_exempt"}
    return {
        "is_domestic": category == "domestic",
        "is_overseas": category == "overseas",
        "needs_withholding": not is_tax_exempt,
        "is_tax_exempt": is_tax_exempt,
        "needs_wire_transfer_clause": category == "overseas",
    }


def validate_nominator_person(person: PersonSourceRow, language: str) -> None:
    require_value(person.key, "person-key")
    require_value(person.name.kor, "person-name-kor")
    if language == "eng":
        require_value(person.name.eng, "person-name-eng")
    require_value(person.residence_country, "residence_country")
    require_value(person.workplace, "workplace")


def require_value(value: Any, field_name: str):
    if value in (None, ""):
        raise ValueError(f"필수값이 비어 있습니다: {field_name}")
    return value


def read_nominator_source_values(person: PersonSourceRow) -> dict[str, Any]:
    return {
        field_name: require_value(
            _mapped_value(person.raw_by_header, aliases),
            field_name,
        )
        for field_name, aliases in NOMINATOR_CONTEXT_FIELDS.items()
    }


def _mapped_value(row: dict[str, Any], aliases: set[str]) -> Any:
    normalized_aliases = {_normalize_header(alias) for alias in aliases}
    for header, value in row.items():
        if _normalize_header(header) in normalized_aliases:
            return value
    return None


def _normalize_header(value: Any) -> str:
    return str(value or "").strip().replace("-", "_").lower()


# 000,000,000 단위로 숫자 포맷팅
def _format_number(value: Any) -> str:
    return f"{round(float(value)):,}"


def _format_rate(value: Any) -> str:
    numeric = float(value)
    if 0 <= numeric <= 1:
        numeric *= 100
    return f"{numeric:g}%"
