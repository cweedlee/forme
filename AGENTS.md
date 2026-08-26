# AGENTS.md

이 파일은 Codex 및 기타 coding agent가 이 저장소를 수정할 때 따라야 할 프로젝트 규칙입니다.

---

## 1. Project Intent

이 저장소는 **UnfoldX 내부 계약업무를 위한 프로젝트 전용 로컬 웹앱**이다.

범용 SaaS, 범용 계약관리 플랫폼, 범용 문서 생성 플랫폼으로 확장하지 않는다.

현재 업무를 해결하는 가장 단순한 구현을 우선한다.

---

## 2. Core Architecture

기본 구조는 다음을 유지한다.

```text
Office LAN
    ↓
Django Local Server
    ↓
Device ID Access Control
    ↓
Project
    ↓
People
    ↓
Fixed Engagement Type
    ↓
Fixed DOCX Template
    ↓
docxtpl
    ↓
Generated DOCX Snapshot
```

Agent는 명시적인 요청 없이 이 구조를 다른 인증/문서/템플릿 플랫폼으로 대체하지 않는다.

---

## 3. Hard Constraints

다음 항목은 명시적으로 변경 요청을 받지 않는 이상 유지한다.

### 3.1 Network

- 서비스는 local office network 사용을 전제로 한다.
- public SaaS deployment를 전제로 설계하지 않는다.
- IP 주소를 사용자 인증 또는 권한 판단의 primary key로 사용하지 않는다.

### 3.2 Device identity

- 사용자/단말 구분은 Django의 장기 유지 server-side session을 사용한다.
- 최초 접속 시 서버가 session에 random UUID Device ID를 발급하고, 브라우저에는 session cookie만 저장한다.
- session cookie는 브라우저 종료 후에도 유지되도록 만료 기간을 명시한다.
- IP는 로그용 auxiliary metadata로만 사용할 수 있다.
- Device ID → display name / project / admin mapping을 사용한다.
- Device 관리 UI를 자동으로 추가하지 않는다.

### 3.3 Projects

- Project는 DB 모델로 관리한다.
- 프로젝트 초기값과 허용 목록은 코드 또는 명시적 설정으로 관리하고 DB와 동기화한다.
- "새 프로젝트 만들기" UI를 추가하지 않는다.
- 프로젝트별 People/Contract/Log 접근은 분리한다.

### 3.4 Contract types

- 가장 큰 계약 분류는 참여유형으로 하며 `exhibition`, `performance`, `artist_talk`, `academic_presentation`, `nominator`, `juror`를 코드에 정의한다.
- 참여유형, 계약상대 유형, 세법상 거주국, 실제 수행장소, 세무분류를 하나의 contract type으로 합치지 않고 독립된 값으로 관리한다.
- 세무분류와 국가별 세율·필요서류는 코드/config에 명시적으로 하드코딩한다.
- 판단이 불명확하면 임의의 세율로 생성하지 않고 `MANUAL_REVIEW`로 처리한다.
- DB 기반 dynamic contract type builder를 만들지 않는다.
- Tax Rule DB와 범용 세무 rule engine을 만들지 않는다.
- 웹 UI에서 참여유형 생성/삭제/복제 기능을 추가하지 않는다.

### 3.5 Templates

- 계약서 원본은 DOCX를 사용한다.
- HTML → DOCX 변환을 기본 방식으로 사용하지 않는다.
- 실제 계약서 DOCX의 formatting을 보존하는 방향으로 구현한다.
- `docxtpl`을 기본 renderer로 사용한다.
- 웹 기반 DOCX editor를 만들지 않는다.
- template upload UI를 만들지 않는다.
- base contract editing UI를 만들지 않는다.
- 1차 개발에서는 참여유형별 완성 DOCX 6개를 사용한다.
- COMMON + 제9조 모듈의 런타임 조립은 구현하지 않는다.
- 공통조항 변경 시 6개 템플릿을 모두 갱신하고 각각 검증한다.

### 3.6 Per-person overrides

- 인물별 계약 조항 수정 기능을 만들지 않는다.
- 특정 인물 예외는 생성된 DOCX를 Word에서 후편집하는 것을 기본 흐름으로 한다.

### 3.7 People Import

- Excel source schema는 명시적 mapping으로 처리한다.
- 범용 column mapping UI를 만들지 않는다.
- 임의 workbook을 선택하는 UI를 만들지 않는다.
- 운영 workbook이 확정되면 workbook/sheet identifier는 config로 관리한다.
- row identity, update, missing-row, duplicate, validation, transaction 규칙은 프로젝트별 코드/config에 명시적으로 하드코딩한다.
- import는 전체 행을 먼저 검증하고 transaction 안에서 반영한다.
- 원본에서 사라진 Person은 삭제하지 않고 inactive 상태로 전환한다.

### 3.8 API

- 외부 공개 API를 만들지 않는다.
- 내부 frontend에 필요한 endpoint만 구현한다.
- 요구되지 않은 GraphQL/plugin/webhook system을 추가하지 않는다.

---

## 4. Do Not Generalize Without Request

Agent가 자주 하는 과잉설계를 금지한다.

명시적인 요구가 없다면 다음을 만들지 않는다.

```text
- generic template engine
- generic workflow engine
- rule builder
- form builder
- project builder
- role builder
- permission editor
- plugin architecture
- generic import mapper
- generic export engine
- public REST API
- external user signup
- SSO
- cloud multi-tenancy
- automatic schema designer
```

현재 요구사항을 30~100줄의 명시적 코드로 해결할 수 있다면,
그것을 범용 framework로 추상화하지 않는다.

---

## 5. Data Model Guidance

권장 핵심 entity:

```text
Project
Device
Person
GeneratedContract
AuditLog
```

Engagement Type과 Template Registry는 코드/config에서 관리한다.

별도 `ContractAssessment`, Tax Rule snapshot, 계약 체결 완료, 지급 완료 모델은 1차 개발에 추가하지 않는다.

DB entity가 반드시 필요한 이유가 생기기 전까지 dynamic Template 모델을 추가하지 않는다.

---

## 6. GeneratedContract

`GeneratedContract`는 단순한 다운로드 기록이 아니라 **snapshot record**다.

최소 필드:

```text
id
project
person
engagement_type
tax_classification
template_version
file_path
generated_at
generated_by_device
last_downloaded_at
last_downloaded_by_device
```

여러 번 생성되면 과거 파일을 덮어쓰지 않는다.

모든 다운로드 이력은 `AuditLog(CONTRACT_DOWNLOADED)`에 누적한다. `last_downloaded_*`는 조회 편의를 위한 최근 상태일 뿐 감사 이력의 원본이 아니다.

생성 파일 경로는 다음 규칙을 사용한다.

```text
data/output/{project}/{engagement_type_code}{person_id}_{safe_person_name}/{contract_language}_{safe_person_name}_{generated_contract_timecode}.docx
```

- `person_name`은 path separator, 제어문자, 예약문자를 제거한 `safe_person_name`으로 변환한다.
- `contract_language`는 코드에 정의된 고정값(`kor`/`eng`)만 허용한다.
- `generated_contract_timecode`는 충돌하지 않도록 UTC microseconds를 포함하고, 충돌 시 GeneratedContract ID를 덧붙인다.
- 임시 파일에 생성하고 DOCX 검증과 DB 저장이 성공한 뒤 atomic rename한다.
- 생성 또는 DB 저장 실패 시 임시/고아 파일을 삭제한다.
- 파일은 정적 경로로 직접 노출하지 않는다. 다운로드 endpoint가 Device/Project 권한을 다시 검사한 뒤 Django `FileResponse`로 전달한다.

---

## 7. Template Version Rule

참여유형별 템플릿 경로, 언어, 현재 버전을 하나의 명시적 registry에서 관리한다.

예:

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

이는 하나의 DOCX를 공유한다는 의미가 아니며, 서로 다른 템플릿 파일을 각각 등록한다.

생성 시 사용한 version number는 기록한다. 기존 생성본의 업데이트 필요 판정과 세무 재계산은 후속 개발 후보이며 1차 개발에 포함하지 않는다.

---

## 8. DOCX Rules

DOCX 작업 시 다음을 확인한다.

### Required

- paragraph style 유지
- font 유지
- font size 유지
- page margin 유지
- table structure 유지
- header/footer 유지
- page break 유지
- signature area 유지

### Avoid

긴 계약 조항 전체를 하나의 plain string placeholder로 밀어 넣어서 formatting을 깨뜨리지 않는다.

1차 개발에서는 참여유형별 완성 템플릿을 분리한다.

```text
exhibition.docx
performance.docx
```

가

```text
common.docx + runtime article module assembly
```

보다 우선이다.

---

## 9. Device ID Implementation

권장 흐름:

```text
Browser first visit
    ↓
No persistent Django session
    ↓
Server creates session and random UUID Device ID
    ↓
Persist long-lived session cookie in browser
    ↓
Server resolves Device config
```

미등록 Device:

```text
HTTP 403 for protected data
```

단, UI에서는 등록 요청에 사용할 Device Code를 표시할 수 있다.

Device ID는 보안성이 높은 사용자 인증 시스템이 아니다.

따라서 화면 문구와 코드에서 이를 "verified user identity"처럼 취급하지 않는다.

Django의 CSRF 보호를 유지하며 session cookie에는 `HttpOnly`, `SameSite`, 명시적인 만료 기간을 설정한다. 브라우저 cookie가 삭제되면 새 Device ID가 발급된다.

---

## 10. Security

필수:

- credentials를 git에 commit하지 않는다.
- `.env` 사용
- OAuth token/secret 로그 출력 금지
- path traversal 방지
- 프로젝트 접근권한 server-side 검사
- frontend에서 숨겼다는 이유만으로 접근을 허용하지 않는다.
- 파일 다운로드 endpoint에서도 project/device authorization을 다시 검사한다.
- 생성 파일명과 경로 component를 sanitize하고, 최종 resolved path가 `DATA_ROOT/output` 아래인지 검사한다.

하지 말 것:

- hidden expiration logic
- time bomb
- remote kill switch
- undocumented destructive behavior
- intentionally corrupted output
- secret dependency on a developer-owned server/account

프로그램은 현재 정의된 환경 안에서는 정상적으로 동작해야 한다.

---

## 11. External Drive Provider

Google Drive 또는 Microsoft OneDrive 중 실제 선택된 Provider를 구현한다.

명시적인 요구가 없다면 두 Provider를 동시에 지원하기 위한 큰 abstraction layer를 먼저 만들지 않는다.

개발 초기에는:

```text
local fixture.xlsx
```

로 importer를 테스트한 뒤 실제 Provider를 연결해도 된다.

---

## 12. Frontend Rules

Frontend는 업무 도구다.

우선순위:

```text
clarity
> correctness
> speed
> visual polish
```

과도한 UI framework migration을 하지 않는다.

현재 Vanilla JS + Webpack으로 충분하면 유지한다.

화면 예:

```text
/
  project selector (admin only)

/people
  list
  filters
  status

/people/:id
  person detail
  contract status
  generate/download

/templates
  template type
  version
  history metadata

/logs
  admin only
```

`/templates`는 편집기가 아니다.

---

## 13. Project Access Must Be Server-Side

아래는 금지:

```javascript
if (!allowed) {
    hideMenu();
}
```

만으로 접근을 제한하는 것.

반드시 Django view/service layer에서 검사한다.

예:

```python
if project.slug not in device.allowed_projects:
    raise PermissionDenied()
```

---

## 14. Logging

Audit 이벤트 이름은 명확하고 고정된 문자열을 사용한다.

권장:

```text
DEVICE_SEEN
ACCESS_DENIED
PEOPLE_IMPORT_STARTED
PEOPLE_IMPORT_COMPLETED
PEOPLE_IMPORT_FAILED
CONTRACT_GENERATED
CONTRACT_GENERATION_FAILED
CONTRACT_DOWNLOADED
```

로그에는 credential, access token, 계약서 본문을 저장하지 않는다.

다운로드가 여러 번 발생하면 각각 별도 `CONTRACT_DOWNLOADED` 이벤트로 저장한다.

---

## 14.1 Storage and Recovery

- 실행 중인 SQLite DB는 Google Drive 동기화 폴더에 두지 않는다.
- 생성 DOCX의 `data/output`은 단일 서버에서만 쓰는 Google Drive 동기화 폴더에 둘 수 있다.
- 계약 생성은 임시 파일 → 검증 → DB record 저장 → atomic rename 순으로 처리하고, 실패 시 임시 파일과 고아 파일을 정리한다.
- SQLite DB와 output 파일의 일관된 백업/복구 절차는 운영 전에 별도로 검증한다.

---

## 15. Coding Style

Python:

- type hint 가능한 곳에 사용
- business rule은 view에 직접 쌓지 않는다
- importer / contract generation / access control을 service 단위로 분리
- 지나친 inheritance 피하기
- magic string은 config/constant로 이동

JavaScript:

- browser Device ID 처리
- API 호출
- 화면 렌더링
- 최소한의 client state

권한/참여유형/세무분류 판정 같은 핵심 business rule은 frontend에 두지 않는다.

---

## 16. Suggested Backend Modules

```text
backend/
├── apps/
│   ├── devices/
│   │   ├── services.py
│   │   └── middleware.py
│   │
│   ├── people/
│   │   ├── models.py
│   │   ├── importer.py
│   │   └── services.py
│   │
│   ├── contracts/
│   │   ├── models.py
│   │   ├── generator.py
│   │   ├── registry.py
│   │   └── services.py
│   │
│   └── audit/
│       ├── models.py
│       └── services.py
│
└── project_config/
    ├── projects.py
    ├── devices.py
    ├── engagement_types.py
    ├── tax_rules.py
    └── people_mapping.py
```

---

## 17. Tests

최소한 다음 테스트는 유지한다.

### Device

- registered device can access assigned project
- registered device cannot access other project
- unknown device cannot access protected project
- admin device can access allowed projects

### Import

- known columns map correctly
- missing required column fails clearly
- unknown extra column does not silently corrupt data

### Contract

- correct DOCX template selected by engagement type
- engagement type, counterparty type, residence country, performance location, and tax classification remain separate
- ambiguous tax classification stops generation with MANUAL_REVIEW
- template version stored
- previous GeneratedContract not overwritten
- generated file exists
- generated DOCX can be reopened
- unresolved placeholders do not remain
- repeated generation never overwrites a previous file
- generation failure removes temporary/orphan files

### Authorization

- direct URL access cannot bypass project permission
- contract download cannot bypass project permission

---

## 18. Change Checklist

기능 추가 전 Agent는 내부적으로 아래를 확인한다.

```text
[ ] 현재 요구사항에 실제로 필요한가?
[ ] 기존 project-specific config로 해결 가능한가?
[ ] 불필요한 generic abstraction을 추가하고 있지 않은가?
[ ] 새로운 admin UI가 정말 필요한가?
[ ] project authorization을 server-side에서 검사하는가?
[ ] DOCX formatting을 깨뜨리지 않는가?
[ ] snapshot/history를 보존하는가?
```

---

## 19. When Requirements Are Ambiguous

불명확한 부분이 있더라도 기존 설계 원칙을 유지하면서 가장 작은 구현을 선택한다.

특히 다음을 임의로 추정해 추가하지 않는다.

```text
"나중에 다른 프로젝트에서도 쓸 것 같으니..."
"향후 SaaS가 될 수 있으니..."
"관리자가 직접 설정하고 싶을 수 있으니..."
```

현재 요구된 프로젝트를 기준으로 구현한다.

---

## 20. Definition of Done

기능은 다음을 만족해야 완료로 본다.

1. 실제 업무 흐름에서 동작한다.
2. 프로젝트 접근권한이 server-side에서 검증된다.
3. 기존 데이터 또는 생성된 계약서를 덮어쓰지 않는다.
4. 실패 시 원인을 알 수 있는 오류를 제공한다.
5. credential을 노출하지 않는다.
6. DOCX 결과물이 Word에서 정상적으로 열린다.
7. 불필요한 범용 관리기능을 추가하지 않는다.
8. 관련 테스트가 통과한다.
