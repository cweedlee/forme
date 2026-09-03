import json

from django.http import HttpRequest, JsonResponse
from django.conf import settings
from django.shortcuts import render
from django.urls import path, reverse
from django.views.static import serve
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import never_cache

from config.services.contract_generation import generate_contract_for_person
from config.services.contract_pages import get_contract_page
from config.services.project_settings import load_project_config


def health(_: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@never_cache
def index(request: HttpRequest):
    return render(request, "index.html")


@ensure_csrf_cookie
@never_cache
def contract_page(request: HttpRequest, contract_type: str):
    page = get_contract_page(contract_type)
    if page is None:
        return JsonResponse({"ok": False, "errors": ["지원하지 않는 계약 유형입니다."]}, status=404)

    project_config = load_project_config()
    table = page.table_class.from_workbook(project_config.workbook_path).build()
    return render(
        request,
        page.template_name,
        {
            "table": table,
            "row_count": len(table.rows),
            "data_url": reverse("contract_data", kwargs={"contract_type": contract_type}),
            "generate_url": reverse(
                "contract_generate",
                kwargs={"contract_type": contract_type},
            ),
        },
    )


@never_cache
def contract_data(_: HttpRequest, contract_type: str) -> JsonResponse:
    page = get_contract_page(contract_type)
    if page is None:
        return JsonResponse({"ok": False, "errors": ["지원하지 않는 계약 유형입니다."]}, status=404)

    project_config = load_project_config()
    table = page.table_class.from_workbook(project_config.workbook_path).build()
    response = JsonResponse(
        {
            "sheetName": table.sheet_name,
            "workbookPath": str(table.workbook_path),
            "metadata": table.metadata,
            "columns": table.columns,
            "decisionColumns": table.decision_columns,
            "rows": table.rows,
            "rowCount": len(table.rows),
        }
    )
    response["Cache-Control"] = "no-store, max-age=0"
    return response


@never_cache
def generate_contract(request: HttpRequest, contract_type: str) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"ok": False, "errors": ["POST만 허용됩니다."]}, status=405)

    page = get_contract_page(contract_type)
    if page is None:
        return JsonResponse({"ok": False, "errors": ["지원하지 않는 계약 유형입니다."]}, status=404)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        data_key = str(payload["dataKey"]).strip()
        language = str(payload.get("language", "kor")).strip()
        if not data_key:
            raise ValueError
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "errors": ["dataKey 값이 필요합니다."]}, status=400)

    project_config = load_project_config()
    person = page.table_class.from_workbook(
        project_config.workbook_path
    ).load_person(data_key)
    if not person:
        return JsonResponse(
            {"ok": False, "errors": [f"data-key {data_key}에서 참여자 객체를 만들 수 없습니다."]},
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
    # 사용자 접속 페이지
    path("", index, name="index"),
    path("contracts/<str:contract_type>/", contract_page, name="contract_page"),

    # 내부 API
    path("health/", health, name="health"),
    path("contracts/<str:contract_type>/data/", contract_data, name="contract_data"),
    path(
        "contracts/<str:contract_type>/generate/",
        generate_contract,
        name="contract_generate",
    ),

    # 정적 파일
    path(
        "static/<path:path>",
        static_file,
        name="static",
    ),
]
