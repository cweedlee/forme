from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.conf import settings
from docxtpl import DocxTemplate
from jinja2 import TemplateSyntaxError

from config.services.business_rule_config import load_business_rule_config
from config.services.person_rows import PersonSourceRow
from project_config.nominator_rules import decide_nominator_fee


CONTRACT_TEMPLATE_REGISTRY = {
    "nominator": {
        "template": "temp-norminator.docx",
        "language": "kor",
        "version": 1,
    }
}


@dataclass(frozen=True)
class ContractGenerationResult:
    ok: bool
    output_path: str | None = None
    errors: list[str] | None = None


def generate_contract_for_person(person: PersonSourceRow) -> ContractGenerationResult:
    if person.engagement_type != "nominator":
        return ContractGenerationResult(
            ok=False,
            errors=[f"지원하지 않는 계약서 타입: {person.engagement_type}"],
        )
    return generate_nominator_contract(person)


def generate_nominator_contract(person: PersonSourceRow) -> ContractGenerationResult:
    registry = CONTRACT_TEMPLATE_REGISTRY["nominator"]
    template_path = settings.TEMPLATE_ROOT / registry["template"]
    if not template_path.exists():
        return ContractGenerationResult(
            ok=False,
            errors=[f"템플릿 파일을 찾을 수 없습니다: {template_path}"],
        )

    context = build_nominator_context(person)
    validation_errors = validate_template_context(template_path, context)
    if validation_errors:
        return ContractGenerationResult(ok=False, errors=validation_errors)

    output_path = build_output_path(
        person=person,
        engagement_type="nominator",
        language=registry["language"],
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        doc = DocxTemplate(template_path)
        doc.render(context)
        doc.save(temp_path)
        DocxTemplate(temp_path)
        temp_path.replace(output_path)
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        return ContractGenerationResult(ok=False, errors=[str(exc)])

    return ContractGenerationResult(ok=True, output_path=str(output_path))


def build_nominator_context(person: PersonSourceRow) -> dict[str, Any]:
    config = load_business_rule_config()
    fee_decision = decide_nominator_fee(person, config.nominator)
    gross_amount = fee_decision.amount_krw or 0
    tax_rate = 8.8 if fee_decision.category == "domestic" else 0
    tax_amount = round(gross_amount * tax_rate / 100)
    final_amount = gross_amount - tax_amount
    return {
        "participant_name": person.name,
        "country_code": person.country_code,
        "gross_amount": _format_number(gross_amount),
        "tax_rate": tax_rate,
        "tax_amount": _format_number(tax_amount),
        "final_amount": _format_number(final_amount),
        "payment_clause": _payment_clause(fee_decision.category, gross_amount, tax_rate),
    }


def validate_template_context(template_path: Path, context: dict[str, Any]) -> list[str]:
    try:
        template = DocxTemplate(template_path)
        template_variables = template.get_undeclared_template_variables()
    except TemplateSyntaxError as exc:
        return [f"템플릿 변수 문법 오류: {exc.message}"]

    context_variables = set(context.keys())
    missing = sorted(template_variables - context_variables)
    unused = sorted(context_variables - template_variables)
    errors = []
    if missing:
        errors.append(f"템플릿에 필요한 값이 함수 context에 없습니다: {', '.join(missing)}")
    if unused:
        errors.append(f"함수 context 값이 템플릿에서 사용되지 않습니다: {', '.join(unused)}")
    return errors


def build_output_path(*, person: PersonSourceRow, engagement_type: str, language: str) -> Path:
    timecode = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    safe_name = sanitize_path_component(person.name or "unknown")
    directory = settings.OUTPUT_ROOT / engagement_type / f"{person.source_row}_{safe_name}"
    filename = f"{language}_{safe_name}_{timecode}.docx"
    return directory / filename


def sanitize_path_component(value: str) -> str:
    blocked = '<>:"/\\|?*'
    cleaned = "".join("_" if char in blocked or ord(char) < 32 else char for char in value)
    cleaned = cleaned.strip().strip(".")
    return cleaned or "unknown"


def _format_number(value: int) -> str:
    return f"{value:,}"


def _payment_clause(category: str | None, gross_amount: int, tax_rate: float) -> str:
    if category == "domestic":
        return f"③ 계약금액 {_format_number(gross_amount)}원에서 {tax_rate}%의 원천징수세액을 공제한 금액을 지급한다."
    if category == "overseas":
        return f"③ 국외 노미네이터가 대한민국에 입국하지 않고 추천업무 전부를 해외에서 온라인으로 수행하는 경우에는 대한민국 내 원천징수 없이 계약금액 {_format_number(gross_amount)}원을 지급한다."
    return "③ 지급 조건은 수동 검토 후 확정한다."
