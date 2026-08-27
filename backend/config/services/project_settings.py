import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings


ALLOWED_ENGAGEMENT_TYPES = {
    "exhibition",
    "performance",
    "artist_talk",
    "academic_presentation",
    "nominator",
    "juror",
}
ALLOWED_LANGUAGES = {"kor", "eng"}


@dataclass(frozen=True)
class TemplateConfig:
    path: Path
    version: int


@dataclass(frozen=True)
class ProjectRuntimeConfig:
    slug: str
    label: str
    workbook_path: Path
    people_sheets: dict[str, str]
    people_layouts: dict[str, dict[str, Any]]
    rules_sheet: str
    templates: dict[str, dict[str, TemplateConfig]]
    output_root: Path

    def people_sheet_for(self, engagement_type: str) -> str:
        try:
            return self.people_sheets[engagement_type]
        except KeyError as exc:
            raise ValueError(f"프로젝트 설정에 people sheet가 없습니다: {engagement_type}") from exc

    def people_layout_for(self, engagement_type: str) -> dict[str, Any]:
        return self.people_layouts.get(
            engagement_type,
            {
                "nature_header_row": 1,
                "code_header_row": 2,
                "data_first_row": 3,
                "visible_columns": [],
            },
        )

    def template_for(self, engagement_type: str, language: str) -> TemplateConfig:
        try:
            return self.templates[engagement_type][language]
        except KeyError as exc:
            raise ValueError(f"프로젝트 설정에 템플릿이 없습니다: {engagement_type}/{language}") from exc


@lru_cache(maxsize=8)
def load_project_config(project_slug: str | None = None) -> ProjectRuntimeConfig:
    slug = project_slug or settings.CURRENT_PROJECT_SLUG
    config_path = settings.PROJECTS_CONFIG_PATH
    with config_path.open(encoding="utf-8") as config_file:
        raw_projects = json.load(config_file)

    try:
        raw_project = raw_projects[slug]
    except KeyError as exc:
        raise ValueError(f"프로젝트 설정을 찾을 수 없습니다: {slug}") from exc

    return parse_project_config(slug, raw_project)


def parse_project_config(slug: str, raw_project: dict[str, Any]) -> ProjectRuntimeConfig:
    people_sheets = {
        _validate_engagement_type(engagement_type): str(sheet_name).strip()
        for engagement_type, sheet_name in (raw_project.get("people_sheets") or {}).items()
        if str(sheet_name).strip()
    }
    people_layouts = {
        _validate_engagement_type(engagement_type): {
            "nature_header_row": int(layout.get("nature_header_row") or 1),
            "code_header_row": int(layout.get("code_header_row") or 2),
            "data_first_row": int(layout.get("data_first_row") or 3),
            "visible_columns": [
                str(column).strip()
                for column in layout.get("visible_columns", [])
                if str(column).strip()
            ],
        }
        for engagement_type, layout in (raw_project.get("people_layouts") or {}).items()
    }
    templates = {
        _validate_engagement_type(engagement_type): _parse_language_templates(language_templates)
        for engagement_type, language_templates in (raw_project.get("templates") or {}).items()
    }
    config = ProjectRuntimeConfig(
        slug=slug,
        label=str(raw_project.get("label") or slug),
        workbook_path=_resolve_project_path(raw_project["workbook"]),
        people_sheets=people_sheets,
        people_layouts=people_layouts,
        rules_sheet=str(raw_project.get("rules_sheet") or "Rules"),
        templates=templates,
        output_root=_resolve_project_path(raw_project.get("output_root") or "data/output"),
    )
    validate_project_config(config)
    return config


def validate_project_config(config: ProjectRuntimeConfig) -> None:
    if not config.workbook_path.exists():
        raise ValueError(f"프로젝트 workbook 파일을 찾을 수 없습니다: {config.workbook_path}")
    if not config.people_sheets:
        raise ValueError("프로젝트 people_sheets 설정이 비어 있습니다.")
    for engagement_type, language_templates in config.templates.items():
        if not language_templates:
            raise ValueError(f"프로젝트 템플릿 설정이 비어 있습니다: {engagement_type}")
        for language, template in language_templates.items():
            if not template.path.exists():
                raise ValueError(f"프로젝트 템플릿 파일을 찾을 수 없습니다: {language}: {template.path}")


def _parse_language_templates(raw_templates: dict[str, Any]) -> dict[str, TemplateConfig]:
    return {
        _validate_language(language): TemplateConfig(
            path=_resolve_project_path(raw_template["path"]),
            version=int(raw_template.get("version") or 1),
        )
        for language, raw_template in raw_templates.items()
    }


def _resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (settings.BASE_DIR.parent / path).resolve()


def _validate_engagement_type(value: str) -> str:
    normalized = str(value).strip()
    if normalized not in ALLOWED_ENGAGEMENT_TYPES:
        raise ValueError(f"허용되지 않은 참여유형입니다: {normalized}")
    return normalized


def _validate_language(value: str) -> str:
    normalized = str(value).strip()
    if normalized not in ALLOWED_LANGUAGES:
        raise ValueError(f"허용되지 않은 계약서 언어입니다: {normalized}")
    return normalized
