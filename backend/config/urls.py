from django.contrib import admin
from django.http import HttpRequest, JsonResponse
from django.conf import settings
from django.shortcuts import render
from django.urls import path

from config.services.people_source import load_people_table


def health(_: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


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


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("people/", people, name="people"),
    path("people/data/", people_data, name="people_data"),
]
