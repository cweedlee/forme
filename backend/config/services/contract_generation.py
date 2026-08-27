from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.conf import settings
from docx import Document
from docxtpl import DocxTemplate
from jinja2 import TemplateSyntaxError

from config.services.business_rule_config import load_business_rule_config
from config.services.person_rows import PersonSourceRow
from project_config.nominator_rules import decide_nominator_fee


class PaymentClauseError(ValueError):
    pass


REMOVE_PARAGRAPH_SENTINEL = "__UNFOLDX_REMOVE_PARAGRAPH__"
OPTIONAL_CLAUSE_KEYS = {"payment_clause_2"}


CONTRACT_TEMPLATE_REGISTRY = {
    "nominator": {
        "templates": {
            "kor": "norminator-kor.docx",
            "eng": "norminator-eng.docx",
        },
        "version": 1,
    }
}


@dataclass(frozen=True)
class ContractGenerationResult:
    ok: bool
    output_path: str | None = None
    errors: list[str] | None = None


def generate_contract_for_person(person: PersonSourceRow, language: str = "kor") -> ContractGenerationResult:
    if person.engagement_type != "nominator":
        return ContractGenerationResult(
            ok=False,
            errors=[f"지원하지 않는 계약서 타입: {person.engagement_type}"],
        )
    return generate_nominator_contract(person, language)


def generate_nominator_contract(person: PersonSourceRow, language: str = "kor") -> ContractGenerationResult:
    if language not in {"kor", "eng"}:
        return ContractGenerationResult(ok=False, errors=[f"지원하지 않는 언어: {language}"])

    registry = CONTRACT_TEMPLATE_REGISTRY["nominator"]
    template_path = settings.TEMPLATE_ROOT / registry["templates"][language]
    if not template_path.exists():
        return ContractGenerationResult(
            ok=False,
            errors=[f"템플릿 파일을 찾을 수 없습니다: {template_path}"],
        )

    try:
        context = build_nominator_context(person, language)
    except PaymentClauseError as exc:
        return ContractGenerationResult(ok=False, errors=[str(exc)])

    validation_errors = validate_template_context(template_path, context)
    if validation_errors:
        return ContractGenerationResult(ok=False, errors=validation_errors)

    output_path = build_output_path(
        person=person,
        engagement_type="nominator",
        language=language,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        doc = DocxTemplate(template_path)
        doc.render(context)
        doc.save(temp_path)
        remove_sentinel_paragraphs(temp_path)
        DocxTemplate(temp_path)
        temp_path.replace(output_path)
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        return ContractGenerationResult(ok=False, errors=[str(exc)])

    return ContractGenerationResult(ok=True, output_path=str(output_path))


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


def validate_template_context(template_path: Path, context: dict[str, Any]) -> list[str]:
    try:
        template = DocxTemplate(template_path)
        template_variables = template.get_undeclared_template_variables()
    except TemplateSyntaxError as exc:
        return [f"템플릿 변수 문법 오류: {exc.message}"]

    context_variables = set(context.keys())
    missing = sorted(template_variables - context_variables)
    errors = []
    if missing:
        errors.append(f"템플릿에 필요한 값이 함수 context에 없습니다: {', '.join(missing)}")
    return errors


def build_output_path(*, person: PersonSourceRow, engagement_type: str, language: str) -> Path:
    timecode = datetime.now(timezone.utc).strftime("%y%m%d-%H:%M")
    safe_folder_name = sanitize_path_component(person.name.kor or "unknown")
    safe_file_name = sanitize_path_component(person_name_for_language(person, language))
    safe_key = sanitize_path_component(person.key or f"row{person.source_row}")
    directory = settings.OUTPUT_ROOT / engagement_type / f"[{safe_key}]{safe_folder_name}"
    filename = f"{safe_file_name}_{timecode}.docx"
    return directory / filename


def person_name_for_language(person: PersonSourceRow, language: str) -> str:
    if language == "eng":
        return person.name.eng or person.name.kor or "unknown"
    return person.name.kor or person.name.eng or "unknown"


def sanitize_path_component(value: str) -> str:
    blocked = '<>:"/\\|?*'
    cleaned = "".join("_" if char in blocked or ord(char) < 32 else char for char in value)
    cleaned = cleaned.strip().strip(".")
    return cleaned or "unknown"


def optional_clause_value(payment_clauses: dict[str, str], key: str) -> str:
    value = payment_clauses.get(key, "")
    if value or key not in OPTIONAL_CLAUSE_KEYS:
        return value
    return REMOVE_PARAGRAPH_SENTINEL


def remove_sentinel_paragraphs(docx_path: Path) -> None:
    document = Document(docx_path)
    for paragraph in list(iter_document_paragraphs(document)):
        if REMOVE_PARAGRAPH_SENTINEL in paragraph.text:
            paragraph._element.getparent().remove(paragraph._element)
    document.save(docx_path)


def iter_document_paragraphs(container):
    for paragraph in getattr(container, "paragraphs", []):
        yield paragraph
    for table in getattr(container, "tables", []):
        for row in table.rows:
            for cell in row.cells:
                yield from iter_document_paragraphs(cell)


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
