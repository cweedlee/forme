from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from docx import Document
from docxtpl import DocxTemplate
from jinja2 import TemplateSyntaxError

from config.services.person_rows import PersonSourceRow
from config.services.project_settings import ALLOWED_LANGUAGES, load_project_config


REMOVE_PARAGRAPH_SENTINEL = "__UNFOLDX_REMOVE_PARAGRAPH__"
OPTIONAL_CLAUSE_KEYS = {"payment_clause_2"}
SEOUL_TZ = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True)
class ContractGenerationResult:
    ok: bool
    output_path: str | None = None
    errors: list[str] | None = None


def generate_contract_for_person(person: PersonSourceRow, language: str = "kor") -> ContractGenerationResult:
    engagement_type = person.engagement_type
    if engagement_type != "nominator":
        return ContractGenerationResult(
            ok=False,
            errors=[f"지원하지 않는 계약서 타입: {engagement_type}"],
        )
    if language not in ALLOWED_LANGUAGES:
        return ContractGenerationResult(ok=False, errors=[f"지원하지 않는 언어: {language}"])

    project_config = load_project_config()
    try:
        template_path = project_config.template_for(engagement_type, language).path
    except ValueError as exc:
        return ContractGenerationResult(ok=False, errors=[str(exc)])

    if not template_path.exists():
        return ContractGenerationResult(
            ok=False,
            errors=[f"템플릿 파일을 찾을 수 없습니다: {template_path}"],
        )

    try:
        context = build_contract_context(person, language)
    except ValueError as exc:
        return ContractGenerationResult(ok=False, errors=[str(exc)])

    validation_errors = validate_template_context(template_path, context)
    if validation_errors:
        return ContractGenerationResult(ok=False, errors=validation_errors)

    output_path = build_output_path(
        person=person,
        engagement_type=engagement_type,
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


def generate_nominator_contract(person: PersonSourceRow, language: str = "kor") -> ContractGenerationResult:
    return generate_contract_for_person(person, language)


def build_contract_context(person: PersonSourceRow, language: str) -> dict[str, object]:
    if person.engagement_type == "nominator":
        from config.services.nominator_contract import build_nominator_context

        return build_nominator_context(person, language)
    raise ValueError(f"지원하지 않는 계약서 타입: {person.engagement_type}")


def validate_template_context(template_path: Path, context: dict[str, Any]) -> list[str]:
    try:
        template = DocxTemplate(template_path)
        template_variables = template.get_undeclared_template_variables()
    except TemplateSyntaxError as exc:
        if "unknown tag 'p'" in str(exc):
            return []
        return [f"템플릿 변수 문법 오류: {exc.message}"]

    context_variables = set(context.keys())
    missing = sorted(template_variables - context_variables)
    errors = []
    if missing:
        errors.append(f"템플릿에 필요한 값이 함수 context에 없습니다: {', '.join(missing)}")
    return errors


def build_output_path(*, person: PersonSourceRow, engagement_type: str, language: str) -> Path:
    project_config = load_project_config()
    timecode = datetime.now(SEOUL_TZ).strftime("%y%m%d-%H%M%S%f")
    safe_folder_name = sanitize_path_component(person.name.kor or "unknown")
    safe_file_name = sanitize_path_component(person_name_for_language(person, language))
    safe_key = sanitize_path_component(person.key or f"row{person.source_row}")
    directory = project_config.output_root / engagement_type / f"[{safe_key}]{safe_folder_name}"
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
