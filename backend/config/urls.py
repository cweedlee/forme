from django.contrib import admin
import json

from django.http import HttpRequest, JsonResponse
from django.conf import settings
from django.shortcuts import render
from django.urls import path
from django.views.decorators.csrf import ensure_csrf_cookie

from config.services.contract_generation import generate_contract_for_person
from config.services.people_source import load_people_table, load_person_from_workbook


def health(_: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@ensure_csrf_cookie
def people(request: HttpRequest):
    table = load_people_table(settings.UNFOLDX_USER_DATA_WORKBOOK)
    return render(
        request,
        "people.html",
        {
            "table": table,
            "row_count": len(table.rows),
        },
    )


def people_data(_: HttpRequest) -> JsonResponse:
    table = load_people_table(settings.UNFOLDX_USER_DATA_WORKBOOK)
    return JsonResponse(
        {
            "sheetName": table.sheet_name,
            "workbookPath": str(table.workbook_path),
            "columns": table.columns,
            "decisionColumns": table.decision_columns,
            "rows": table.rows,
            "rowCount": len(table.rows),
        }
    )


def generate_people_contract(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"ok": False, "errors": ["POST만 허용됩니다."]}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        source_row = int(payload["sourceRow"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "errors": ["sourceRow 값이 필요합니다."]}, status=400)

    person = load_person_from_workbook(settings.UNFOLDX_USER_DATA_WORKBOOK, source_row)
    if not person:
        return JsonResponse(
            {"ok": False, "errors": [f"source row {source_row}에서 참여자 객체를 만들 수 없습니다."]},
            status=400,
        )

    result = generate_contract_for_person(person)
    status = 200 if result.ok else 400
    return JsonResponse(
        {
            "ok": result.ok,
            "outputPath": result.output_path,
            "errors": result.errors or [],
        },
        status=status,
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("people/", people, name="people"),
    path("people/data/", people_data, name="people_data"),
    path("people/generate/", generate_people_contract, name="generate_people_contract"),
]
