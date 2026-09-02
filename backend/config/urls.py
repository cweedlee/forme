from django.contrib import admin
import json

from django.http import HttpRequest, JsonResponse
from django.conf import settings
from django.shortcuts import render
from django.urls import path, reverse
from django.views.static import serve
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import never_cache

from config.services.contract_generation import generate_contract_for_person
from config.services.nominator_source import load_nominator_person_from_workbook, load_nominator_table
from config.services.project_settings import load_project_config


def health(_: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@never_cache
def index(request: HttpRequest):
    return render(request, "index.html")


@ensure_csrf_cookie
@never_cache
def nominator(request: HttpRequest):
    project_config = load_project_config()
    table = load_nominator_table(
        project_config.workbook_path,
        sheet_name=project_config.people_sheet_for("nominator"),
    )
    return render(
        request,
        "nominator.html",
        {
            "table": table,
            "row_count": len(table.rows),
            "data_url": reverse("nominator_data"),
            "generate_url": reverse("nominator_generate"),
        },
    )


@never_cache
def nominator_data(_: HttpRequest) -> JsonResponse:
    project_config = load_project_config()
    table = load_nominator_table(
        project_config.workbook_path,
        sheet_name=project_config.people_sheet_for("nominator"),
    )
    response = JsonResponse(
        {
            "sheetName": table.sheet_name,
            "workbookPath": str(table.workbook_path),
            "metadata": table.metadata,
            "columns": table.columns,
            "fieldKeys": table.field_keys,
            "decisionColumns": table.decision_columns,
            "rows": table.rows,
            "rowCount": len(table.rows),
        }
    )
    response["Cache-Control"] = "no-store, max-age=0"
    return response


@never_cache
def generate_nominator_contract(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"ok": False, "errors": ["POST만 허용됩니다."]}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        source_row = int(payload["sourceRow"])
        language = str(payload.get("language", "kor")).strip()
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "errors": ["sourceRow 값이 필요합니다."]}, status=400)

    project_config = load_project_config()
    person = load_nominator_person_from_workbook(
        project_config.workbook_path,
        source_row,
        sheet_name=project_config.people_sheet_for("nominator"),
    )
    if not person:
        return JsonResponse(
            {"ok": False, "errors": [f"source row {source_row}에서 참여자 객체를 만들 수 없습니다."]},
            status=400,
        )

    result = generate_contract_for_person(person, language)
    status = 200 if result.ok else 400
    return JsonResponse(
        {
            "ok": result.ok,
            "outputPath": result.output_path,
            "errors": result.errors or [],
        },
        status=status,
    )


@never_cache
def static_file(request: HttpRequest, path: str):
    return serve(request, path, document_root=settings.STATIC_ROOT)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", index, name="index"),
    path("health/", health, name="health"),
    path("nominator/", nominator, name="nominator"),
    path("nominator/data/", nominator_data, name="nominator_data"),
    path("nominator/generate/", generate_nominator_contract, name="nominator_generate"),
    path("people/", nominator, name="people"),
    path("people/data/", nominator_data, name="people_data"),
    path("people/generate/", generate_nominator_contract, name="generate_people_contract"),
    path(
        "static/<path:path>",
        static_file,
        name="static",
    ),
]
