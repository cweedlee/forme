# UnfoldX Contract Tool

UnfoldX 내부 계약 업무를 보조하기 위한 **사무실 LAN 전용 계약서 생성/관리 웹앱**입니다.

이 프로젝트는 범용 계약관리 SaaS가 아니라, 정해진 프로젝트·정해진 계약 유형·정해진 인명록 구조를 대상으로 동작하는 **프로젝트 전용 내부 도구**입니다.

---

## 1. 목적

반복되는 계약 업무를 줄이는 것이 목적입니다.

주요 흐름:

1. Google Drive 또는 Microsoft OneDrive에 있는 지정 Excel 파일에서 계약 대상자 정보를 가져온다.
2. 참여유형을 가장 큰 분류로 두고 계약상대 유형, 세법상 거주국, 실제 수행장소를 각각 확인한다.
3. 코드/config에 명시된 세무 규칙으로 세무분류와 금액을 판단한다.
4. 참여유형별 DOCX 템플릿에 대상자와 계약 데이터를 주입한다.
5. 완성된 Word 계약서를 다운로드한다.
6. 어떤 템플릿 버전으로 언제 계약서를 생성/다운로드했는지 기록한다.

템플릿 또는 세무조건 변경에 따른 업데이트 판정은 1차 개발 범위에 포함하지 않고 후속 개발 후보로 기록합니다.

---

## 2. 프로젝트 범위

### 포함

- 사무실 내부 네트워크에서만 접속
- 브라우저의 장기 유지 Django session별 Device ID 발급
- Device ID별 사용자명/프로젝트 접근권한 매핑
- 지정된 Excel 파일에서 People 데이터 Import
- 고정된 참여유형과 세무분류 규칙
- 참여유형별 DOCX 템플릿 6개
- DOCX 계약서 생성 및 다운로드
- 생성 시 사용한 템플릿 버전 기록
- 계약서 생성/다운로드 기록
- 프로젝트별 데이터 분리
- 관리자 Device에서 템플릿 버전 및 로그 확인


---

## 3. 권장 기술 스택

```text
Backend
- Python
- Django
- SQLite
- docxtpl

Frontend
- Vanilla JavaScript
- Webpack
- HTML / CSS

Deployment
- Docker
- Docker Compose

Document
- DOCX
- docxtpl

External data
- Google Drive OR Microsoft OneDrive
```

하나의 외부 저장소 Provider만 실제 운영에 사용합니다.

Google Drive와 OneDrive를 동시에 지원하기 위한 범용 추상화는 요구사항이 생기기 전까지 만들지 않습니다.

---

## 4. 전체 구조

```text
Google Drive / OneDrive
        │
        │ 지정된 Workbook
        ▼
┌──────────────────────┐
│   People Importer    │
│ fixed column mapping │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│      People DB       │
└──────────┬───────────┘
           │
           ▼
┌────────────────────────────┐
│     Contract Generator     │
│                            │
│ fixed contract type        │
│ fixed DOCX template        │
│ person data                │
└──────────────┬─────────────┘
               ▼
       Generated DOCX
               │
               ├── download
               │
               └── generation/download log
```

접근 제어:

```text
Office LAN
    │
    ▼
Local Django Server
    │
    ▼
Browser
    │
    ▼
Device ID
    │
    ├── display name
    ├── allowed projects
    └── admin 여부
```

---

## 5. Device ID

사무실 IP는 DHCP로 동적 할당되므로 IP 주소를 사용자 식별자로 사용하지 않습니다.

브라우저가 최초 접속할 때 Django 서버가 장기 유지 session을 만들고, session 안에 랜덤 Device ID를 생성합니다. 브라우저에는 `HttpOnly` session cookie만 저장합니다.

예:

```text
ux26-6d4518b9-0ea2-4a37-9d15-...
```

Device ID는 server-side session에 저장합니다. Session cookie는 브라우저 종료 후에도 유지되도록 만료 기간을 명시하며 `HttpOnly`, `SameSite` 설정과 Django CSRF 보호를 사용합니다.

서버에는 다음과 같이 등록합니다.

```python
DEVICE_ACCESS = {
    "ux26-device-a": {
        "name": "기획팀 PC",
        "projects": ["unfoldx"],
        "admin": False,
    },
    "ux26-device-b": {
        "name": "운영팀 PC",
        "projects": ["project_b"],
        "admin": False,
    },
    "ux26-admin": {
        "name": "관리자 PC",
        "projects": ["unfoldx", "project_b"],
        "admin": True,
    },
}
```

### 원칙

- IP는 로그 참고용으로만 저장할 수 있다.
- 권한 판단에 IP를 사용하지 않는다.
- Device ID가 등록되어 있지 않으면 프로젝트 상세 정보 접근을 거부한다.
- 관리자용 Device 등록 UI는 만들지 않는다.
- Device 추가/변경은 설정 파일 또는 관리 코드 수정으로 처리한다.

브라우저 데이터가 삭제되면 새로운 Device ID가 발급될 수 있다.

미등록 Device에는 다음 정도만 표시한다.

```text
등록되지 않은 장치입니다.

Device Code:
UX26-AB12-CD34
```

---

## 6. People 데이터

People은 지정된 Excel Workbook에서 가져옵니다.

실제 workbook으로 원하는 수준의 Import가 가능한지는 1차 개발 전에 fixture와 운영 샘플로 검증합니다. Import가 확정되기 전에는 Excel 구조를 전제로 모델을 과도하게 고정하지 않습니다.

예상 필드:

```text
name
address
engagement_type
counterparty_type
tax_residence_country
performance_location
gross_amount
tax_treaty_document_required
tax_treaty_document_submitted
engagement_description
work_or_program_title
engagement_schedule
notes
```

추가로 시스템 내부에서 사용할 수 있는 필드:

```text
id
project
source_row_id
created_at
updated_at
last_imported_at
```

### Excel Mapping

Excel 컬럼 매핑은 코드에 명시합니다.

예:

```python
PEOPLE_COLUMN_MAPPING = {
    "성명": "name",
    "주소": "address",
    "참여유형": "engagement_type",
    "계약상대 유형": "counterparty_type",
    "세법상 거주국": "tax_residence_country",
    "실제 수행장소": "performance_location",
    "계약금액": "gross_amount",
    "조세조약증빙서류 필요여부": "tax_treaty_document_required",
    "조세조약증빙서류 제출여부": "tax_treaty_document_submitted",
    "참여내용": "engagement_description",
    "작품·프로그램명": "work_or_program_title",
    "참여일정": "engagement_schedule",
    "비고": "notes",
}
```

웹 UI에서 컬럼 매핑을 변경하는 기능은 만들지 않습니다.

Workbook/Sheet도 운영 대상이 확정되면 설정값으로 고정합니다.

```python
PEOPLE_SOURCE = {
    "provider": "google",
    "workbook_id": "...",
    "sheet_name": "계약대상자",
}
```

OAuth/API credential은 코드 저장소에 커밋하지 않습니다.

Import의 row identity, update, missing-row, duplicate, validation 규칙은 운영 workbook에 맞춰 코드/config에 하드코딩합니다. 전체 행을 먼저 검증한 뒤 하나의 transaction으로 반영하며, 원본에서 사라진 Person은 삭제하지 않고 inactive 상태로 전환합니다.

---

## 7. 계약 분류와 세무 판단

계약은 하나의 복합 `contract_type`으로 분류하지 않습니다. 가장 큰 분류는 참여유형이며 계약상대 유형, 세법상 거주국, 실제 수행장소, 세무분류를 독립된 값으로 관리합니다.

예:

```python
class EngagementType:
    EXHIBITION = "exhibition"
    PERFORMANCE = "performance"
    ARTIST_TALK = "artist_talk"
    ACADEMIC_PRESENTATION = "academic_presentation"
    NOMINATOR = "nominator"
    JUROR = "juror"
```

계약상대 유형은 `individual`과 `organization`으로 고정합니다. 세무분류는 코드/config의 명시적 규칙으로 계산하며, 불명확한 경우 임의의 세율을 적용하지 않고 `MANUAL_REVIEW`로 처리합니다.

```text
ROYALTY_ARTWORK
INDEPENDENT_SERVICE_KR
ARTIST_ENTERTAINER
NON_KOREAN_SOURCE
MANUAL_REVIEW
```

Tax Rule DB와 범용 rule builder는 1차 개발에서 만들지 않습니다. 참여유형별 분류 로직과 국가별 세율·필요서류는 Python 코드/config에 명시하고 변경 시 테스트 후 재배포합니다.

각 참여유형은 서로 독립적인 DOCX 템플릿과 연결됩니다. 참여유형, 템플릿 경로, 언어, 현재 버전은 하나의 registry entry에 함께 정의합니다.

```python
CONTRACT_REGISTRY = {
    "exhibition": {
        "template": "exhibition.docx",
        "language": "kor",
        "version": 3,
    },
    "performance": {
        "template": "performance.docx",
        "language": "kor",
        "version": 2,
    },
}
```

1차 개발에서는 참여유형별 완성 DOCX 6개를 사용합니다. 공통 제1조~제8조가 중복되므로 공통조항 변경 시 6개 파일을 모두 갱신하고 검증합니다. COMMON과 제9조 모듈을 조립하거나 배포 전에 유형별 DOCX를 컴파일하는 방식은 후속 개발 후보로 둡니다.

---

## 8. DOCX 생성

HTML → DOCX 변환을 사용하지 않습니다.

실제 Word 계약서 `.docx`를 템플릿으로 사용하고 `docxtpl`로 값을 치환합니다.

```text
DOCX Template
     +
Person Data
     ↓
docxtpl
     ↓
Generated DOCX
```

예:

```python
from docxtpl import DocxTemplate


def generate_contract(template_path, output_path, context):
    doc = DocxTemplate(template_path)
    doc.render(context)
    doc.save(output_path)
```

Word 템플릿 안에는 placeholder를 사용합니다.

```text
성명: {{ name }}
주소: {{ residence }}
국가: {{ tax_treaty_country }}
```

### 중요한 원칙

복잡한 계약 유형 차이를 하나의 거대한 템플릿 조건문으로 처리하지 않습니다.

1차 개발에서는 참여유형별 DOCX 파일 자체를 분리합니다.

```text
contracts/
└── templates/
    ├── exhibition.docx
    ├── performance.docx
    ├── artist_talk.docx
    ├── academic_presentation.docx
    ├── nominator.docx
    └── juror.docx
```

---

## 9. 템플릿 버전

각 참여유형 템플릿은 현재 버전을 가집니다.

현재 버전은 위 `CONTRACT_REGISTRY`의 각 타입 entry에서 관리합니다.

계약서를 생성할 때 반드시 사용한 버전을 기록합니다.

```text
person_id
engagement_type
tax_classification
template_version
generated_at
generated_by_device
last_downloaded_at
last_downloaded_by_device
```

생성 시점의 템플릿 버전은 기록하지만, 기존 계약의 `업데이트 필요` 판정과 세무 재계산 기능은 1차 개발에서 구현하지 않습니다.

후속 개발 시에는 템플릿 업데이트와 세무 재검토 상태를 서로 분리합니다. 계약 체결 완료 상태와 지급 완료 상태는 관리 범위에 포함하지 않습니다.

---

## 10. Generated Contract Snapshot

생성된 계약서는 스냅샷으로 보존합니다.

예:

```text
data/output/{project}/{engagement_type_code}{person_id}_{safe_person_name}/
└── {contract_language}_{safe_person_name}_{generated_contract_timecode}.docx
```

예:

```text
data/output/unfoldx/exhibition1024_Hong_Gildong/
└── kor_Hong_Gildong_20260824T071530123456Z.docx
```

사람 이름은 경로 예약문자와 separator를 제거한 안전한 값으로 변환합니다. timecode는 UTC microseconds를 포함하며, 충돌할 경우 GeneratedContract ID를 붙입니다.

DB에는 생성 시점의 주요 metadata를 저장합니다.

```json
{
  "person_id": 1024,
  "engagement_type": "exhibition",
  "tax_classification": "royalty_artwork",
  "template_version": 3,
  "generated_at": "2026-09-03T14:23:18+09:00",
  "generated_by_device": "ux26-device-a"
}
```

별도의 계약판단·세무규칙 snapshot은 1차 개발에서 저장하지 않습니다. 생성에 사용한 참여유형, 세무분류, Gross, 세율, 원천징수액, Net과 생성된 DOCX 파일은 GeneratedContract에 보존합니다. 계약서 본문은 AuditLog에 저장하지 않습니다.

기존 DOCX를 새 템플릿으로 덮어쓰지 않습니다.

### 생성 및 다운로드 흐름

1. 생성 요청의 Device/Project/Person 권한을 서버에서 검사한다.
2. `data/output` 아래 임시 파일에 DOCX를 생성한다.
3. DOCX를 다시 열 수 있고 placeholder가 남지 않았는지 검사한다.
4. GeneratedContract DB record를 저장하고 최종 경로로 atomic rename한다.
5. 생성 응답 또는 별도 다운로드 endpoint에서 해당 GeneratedContract ID를 사용해 다운로드한다.
6. 다운로드 endpoint가 Device/Project 권한과 resolved file path를 다시 검사한 뒤 Django `FileResponse`로 전달한다.

`data/output`은 정적 파일 경로로 직접 공개하지 않습니다. 생성 또는 DB 저장 실패 시 임시 파일과 확인된 고아 파일을 삭제합니다.

---

## 11. 인물별 계약서 수정

웹앱에서 특정 사람의 계약서 내용을 직접 수정하는 기능은 만들지 않습니다.

```text
Person
   +
Engagement Type
   +
Template Version
   ↓
Generated DOCX
```

개별 예외 수정이 필요한 경우:

1. DOCX 다운로드
2. Word에서 수동 수정
3. 필요하면 별도 비고 기록

웹앱은 Word editor가 아닙니다.

---

## 12. 프로젝트 분리

Project는 DB 모델로 관리합니다. 허용되는 프로젝트의 초기값은 코드/설정에 미리 정의하고 배포 시 DB와 동기화합니다.

예:

```python
PROJECTS = {
    "unfoldx": {
        "name": "UnfoldX",
    },
    "project_b": {
        "name": "Project B",
    },
}
```

프로젝트 생성 UI는 만들지 않으며, 코드/config에 없는 Project를 임의로 생성하지 않습니다.

Device별로 접근 가능한 프로젝트를 제한합니다.

일반 Device는 할당된 프로젝트 외의 People/Contract/Log를 조회할 수 없어야 합니다.

---

## 13. 권장 디렉터리

```text
unfoldx-contract-tool/
├── README.md
├── AGENTS.md
├── .env.example
├── docker-compose.yml
│
├── backend/
│   ├── manage.py
│   ├── config/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   │
│   ├── apps/
│   │   ├── devices/
│   │   ├── people/
│   │   ├── contracts/
│   │   └── audit/
│   │
│   ├── project_config/
│   │   ├── projects.py
│   │   ├── devices.py
│   │   ├── engagement_types.py
│   │   ├── tax_rules.py
│   │   └── people_mapping.py
│   │
│   └── contracts/
│       └── templates/
│           ├── exhibition.docx
│           ├── performance.docx
│           ├── artist_talk.docx
│           ├── academic_presentation.docx
│           ├── nominator.docx
│           └── juror.docx
│
├── frontend/
│   ├── src/
│   ├── webpack.config.js
│   └── package.json
│
└── data/
    └── .gitkeep
```

---

## 14. 환경 변수

`.env`는 저장소에 커밋하지 않습니다.

예:

```dotenv
DJANGO_SECRET_KEY=충분히-긴-임의값
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,서버-LAN-IP

APP_BIND_ADDRESS=0.0.0.0
APP_PORT=8000
SESSION_COOKIE_AGE=15552000
TZ=Asia/Seoul
```

`.env.example`을 `.env`로 복사한 뒤 실제 서버 주소와 secret을 설정합니다. 외부 Drive Provider가 확정되면 해당 Provider에 필요한 credential만 추가합니다.

---

## 15. Docker

운영은 Docker Compose 기준으로 합니다.

개발 소스와 운영 데이터는 분리합니다.

```text
Application image
        +
Persistent data volume
```

현재 구성:

```text
Dockerfile       Django 5.2 LTS + Gunicorn image
compose.yaml     app service, healthcheck, persistent data bind mount
data/            SQLite DB와 생성 DOCX 저장
.env             배포 환경값, git 제외
```

최초 실행:

```powershell
Copy-Item .env.example .env
# .env의 DJANGO_SECRET_KEY와 DJANGO_ALLOWED_HOSTS 수정
docker compose up --build -d
docker compose ps
```

상태 확인:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/
docker compose logs app
```

컨테이너 시작 시 migration을 자동 적용하고 Gunicorn을 실행합니다. `data/`만 host bind mount로 영속화하며 애플리케이션 소스는 image에 포함합니다. `0.0.0.0` bind는 사무실 LAN 접근을 위해 사용하되 host firewall에서 private network만 허용해야 합니다.

---

## 16. 로그

최소한 아래 이벤트를 기록합니다.

```text
PEOPLE_IMPORT_STARTED
PEOPLE_IMPORT_COMPLETED
PEOPLE_IMPORT_FAILED
CONTRACT_GENERATED
CONTRACT_GENERATION_FAILED
CONTRACT_DOWNLOADED
ACCESS_DENIED
```

로그 예:

```text
2026-09-03 14:21:03
device=ux26-device-a
event=CONTRACT_DOWNLOADED
project=unfoldx
person_id=1024
template_version=5
```

Device ID는 실제 개인 신원을 보증하는 인증 수단이 아니라 **브라우저/업무 단말 식별값**입니다.

모든 다운로드는 별도의 `CONTRACT_DOWNLOADED` AuditLog로 누적합니다. GeneratedContract의 `last_downloaded_at`, `last_downloaded_by_device`는 최근 상태 표시용이며 감사 이력의 원본이 아닙니다.

---

## 16.1 저장소와 운영 네트워크

- 실행 중인 SQLite DB는 Google Drive 동기화 폴더 밖의 서버 로컬 volume에 둡니다.
- 생성 DOCX가 저장되는 `data/output`은 단일 서버만 쓰는 Google Drive 동기화 폴더로 지정할 수 있습니다.
- Google Drive 동기화본은 편의상 복제본으로 보고, SQLite DB와 output의 일관된 백업/복구 방법은 운영 전에 검증합니다.
- Django는 사무실 LAN에서 사용하는 private IP 대역에서만 접근하도록 호스트 방화벽으로 제한합니다.
- `ALLOWED_HOSTS`에는 실제 서버의 LAN 주소/호스트명만 지정합니다.
- 고정 client IP를 사용자 식별이나 프로젝트 권한 판단에 사용하지 않습니다.

---

## 17. 개발 원칙

이 프로젝트에서 가장 중요한 원칙:

> 필요한 현재 업무를 정확히 해결하되,
> 요구되지 않은 범용 플랫폼 기능을 미리 만들지 않는다.

따라서 새로운 기능을 추가하기 전에 아래를 확인합니다.

1. 현재 실제 업무에 필요한가?
2. 프로젝트 전용 설정으로 해결 가능한가?
3. 새로운 관리 UI가 정말 필요한가?
4. 기존 모델을 범용화하지 않고 더 단순하게 해결할 수 있는가?
5. 계약서 생성 결과가 기존 Word 계약서의 서식을 보존하는가?

---

## 18. 개발 시작 순서

권장 구현 순서:

```text
1. Django 기본 프로젝트
2. Project 모델/설정
3. Device ID 발급 및 접근 제어
4. People 모델
5. Excel Import
6. 참여유형·세무분류 규칙
7. DOCX Template / docxtpl
8. GeneratedContract 저장
9. 생성/다운로드 로그
10. Frontend
11. Docker
```

첫 구현에서는 Google Drive/OneDrive 연동보다 로컬 XLSX fixture로 Import 로직을 먼저 검증해도 됩니다.

---

## 19. 완료 기준

최소 완료 조건:

- [ ] 사무실 네트워크의 서버에서 웹앱 실행 가능
- [ ] 최초 접속 Device ID 발급
- [ ] 등록 Device만 프로젝트 데이터 접근 가능
- [ ] 지정 Excel 데이터 Import 가능
- [ ] People 목록/상세 조회 가능
- [ ] 참여유형별 DOCX 생성 가능
- [ ] 불명확한 세무분류는 MANUAL_REVIEW로 생성 중지
- [ ] Word 서식이 원본과 실질적으로 동일하게 유지
- [ ] 생성된 계약서 Snapshot 저장
- [ ] 생성/다운로드 로그 기록
- [ ] 프로젝트별 데이터 접근 분리

### 후속 개발 후보

- 템플릿 변경에 따른 업데이트 필요 판정
- 세무조건 변경에 따른 재계산 및 경고
- COMMON + 제9조 모듈의 배포 전 DOCX 컴파일
- 계약 체결 완료 및 지급 완료 관리는 현재 범위에서 제외
