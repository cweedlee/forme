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
    sheets: dict[str, str]
    country_code_sheet: str
    data_sheet_layout: dict[str, int | str]
    template_folder: Path
    output_root: Path

    def people_sheet_for(self, engagement_type: str) -> str:
        try:
            return self.sheets[engagement_type]
        except KeyError as exc:
            raise ValueError(f"프로젝트 설정에 people sheet가 없습니다: {engagement_type}") from exc

    def template_for(self, engagement_type: str, language: str) -> TemplateConfig:
        _validate_language(language)
        if engagement_type not in self.sheets:
            raise ValueError(f"프로젝트 설정에 sheet가 없습니다: {engagement_type}")
        return TemplateConfig(
            path=self.template_folder / f"template-{engagement_type}-{language}.docx",
            version=1,
        )


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
    sheets = {
        str(sheet_key).strip(): str(sheet_name).strip()
        for sheet_key, sheet_name in (raw_project.get("sheets") or {}).items()
        if str(sheet_key).strip()
        if str(sheet_name).strip()
    }
    raw_layout = raw_project.get("data-sheet-layout") or {}
    data_sheet_layout: dict[str, int | str] = {
        "data_row": int(raw_layout.get("data-row") or 0),
        "data_column": int(raw_layout.get("data-column") or 0),
        "name_row": int(raw_layout.get("name-row") or 0),
        "var_row": int(raw_layout.get("var-row") or 0),
        "data_key": str(raw_layout.get("data-key") or "").strip(),
    }
    config = ProjectRuntimeConfig(
        slug=slug,
        label=str(raw_project.get("label") or slug),
        workbook_path=_resolve_project_path(raw_project["workbook"]),
        sheets=sheets,
        country_code_sheet=str(raw_project.get("country_code_sheet") or "country-code"),
        data_sheet_layout=data_sheet_layout,
        template_folder=_resolve_project_path(raw_project["template_folder"]),
        output_root=_resolve_project_path(raw_project.get("output_root") or "data/output"),
    )
    validate_project_config(config)
    return config


def validate_project_config(config: ProjectRuntimeConfig) -> None:
    if not config.workbook_path.exists():
        raise ValueError(f"프로젝트 workbook 파일을 찾을 수 없습니다: {config.workbook_path}")
    if not config.sheets:
        raise ValueError("프로젝트 sheets 설정이 비어 있습니다.")
    for field_name, value in config.data_sheet_layout.items():
        if value in (0, ""):
            raise ValueError(f"프로젝트 data-sheet-layout 설정이 비어 있습니다: {field_name}")


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
