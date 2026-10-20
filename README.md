# Pageful — AI 독서 습관 비서

Pageful은 날짜별 독서 시간(분)을 기록하고, 평균·최대·최소·최근 추세를 분석해 개인화된 AI 답변을 제공하는 웹 앱입니다. 과제의 핵심 흐름은 **시계열 기록 → Firestore 저장 → 요약 계산 → 시스템 프롬프트 주입 → OpenAI 답변**입니다.

## 기술 스택

| 영역 | 기술 |
|---|---|
| 백엔드 | Python 3.10+, FastAPI, Uvicorn, Pydantic |
| 데이터베이스·인증 | Firebase Firestore, Firebase Authentication 익명 인증, Firebase Admin SDK |
| AI | OpenAI Responses API |
| 프론트엔드 | HTML, CSS, Vanilla JavaScript, Firebase Web 인증 모듈 |
| 정적 빌드 | esbuild (프레임워크 아님) |
| 배포 | Render(백엔드), Vercel(프론트엔드) |

## 주요 기능

- 날짜·독서 시간·메모 기록 추가, 조회, 수정, 삭제
- 기록 기간, 개수, 총합, 평균, 최대·최소, 최근 7개 기록의 추세 요약
- 실제 최근 7일 독서 시간을 표시하는 그래프
- 요약 정보를 시스템 프롬프트에 넣는 AI 채팅
- 대화 자동 저장, 목록 조회, 이전 대화 불러오기, 삭제
- 로그인 화면 없이 Firebase 익명 인증으로 사용자별 데이터 분리
- AI 요청 중 로딩 표시와 Render 첫 요청 지연 안내

## 데이터 구조

```text
data/{uid}/records/{recordId}
  date: "2026-10-20"
  value: 35                 # 독서 시간, 분
  memo: "책과 메모"
  created_at, updated_at

conversations/{uid}/items/{conversationId}
  title: "최근 독서 습관은?"
  messages: [{role: "user", content: "..."}, {role: "assistant", content: "..."}]
  created_at, updated_at
```

브라우저는 Firebase 익명 로그인 후 받은 ID 토큰을 FastAPI에 전달합니다. FastAPI는 토큰을 검증하고 해당 `uid` 경로만 읽고 씁니다. 브라우저가 Firestore에 직접 접근하지 않도록 [firestore.rules](firestore.rules)는 직접 읽기·쓰기를 거부합니다. Admin SDK는 보안 규칙을 우회하므로 실제 사용자 분리는 백엔드의 토큰 검증과 `uid` 경로 선택에 달려 있습니다.

익명 계정은 보통 같은 브라우저 프로필에서 유지됩니다. 브라우저 데이터를 지우거나 다른 기기로 이동하면 기존 기록을 복구할 로그인 수단이 없습니다. Firebase 프로젝트 관리자 권한이 있다면 저장 데이터를 확인할 수 있으므로 과제용 테스트 데이터를 사용하세요.

## API

모든 `/api/*` 요청에 `Authorization: Bearer <Firebase ID token>` 헤더가 필요합니다.

| 방식 | 경로 | 기능 |
|---|---|---|
| POST | `/api/data` | 기록 추가 |
| GET | `/api/data` | 기록 목록 |
| PUT | `/api/data/{id}` | 기록 수정 |
| DELETE | `/api/data/{id}` | 기록 삭제 |
| GET | `/api/data/summary` | 기간·통계·추세 조회 |
| POST | `/api/conversations` | 대화 저장 |
| GET | `/api/conversations` | 대화 목록 |
| GET | `/api/conversations/{id}` | 전체 메시지 불러오기 |
| DELETE | `/api/conversations/{id}` | 대화 삭제 |
| POST | `/api/chat` | AI 답변과 대화 자동 저장 |

`GET /health`는 배포 상태 확인용입니다. `GET /docs`에서 Swagger UI를 볼 수 있습니다. 입력 오류는 Pydantic의 422 응답 또는 앱의 400 응답으로 전달됩니다.

### 독서 기록 예시

```json
{"date":"2026-10-20","value":35,"memo":"소설 20페이지"}
```

### 채팅 예시

```json
{"message":"최근 독서 습관이 좋아지고 있어?","conversation_id":null}
```

AI 요청 시 백엔드는 해당 사용자의 최신 독서 요약을 조회합니다. 최근 추세는 **최근 7개 기록과 직전 7개 기록의 평균**을 비교해 5% 이상 차이면 상승·하락, 그 외는 유지로 판정합니다. 이전 기록이 충분하지 않으면 데이터 부족으로 표시합니다. AI 응답은 최대 400 출력 토큰으로 제한하고, 질문은 최대 1,000자입니다. OpenAI API 호출에는 비용이 발생할 수 있습니다.

## 사전 준비

1. Python 3.10 이상과 Node.js를 준비합니다.
2. Firebase 프로젝트를 만들고 Firestore Database를 활성화합니다.
3. Firebase Authentication의 **Anonymous** 로그인 방식을 활성화합니다.
4. Firebase Web 앱을 등록하고 공개 Web 설정값을 확인합니다.
5. Firebase 서비스 계정 키 JSON을 발급받습니다.
6. OpenAI API 키를 준비하고 사용할 모델 ID를 정합니다.

서비스 계정 키와 OpenAI API 키는 Git에 올리지 않습니다. `.gitignore`는 `.env`, 로컬 서비스 계정 파일과 가상환경을 제외합니다. Firebase Web 설정값은 브라우저에 전달되는 공개 설정이지만, 서비스 계정 JSON은 절대 프론트엔드에 넣지 않습니다.

## 로컬 실행 (Windows PowerShell)

프로젝트 루트에서 [`.env.example`](.env.example)을 복사해 `.env`를 만들고 값을 채웁니다. 로컬에서는 `FIREBASE_SERVICE_ACCOUNT_PATH`에 서비스 계정 JSON 파일의 절대 경로를 쓰는 편이 편합니다. Render에서는 `FIREBASE_SERVICE_ACCOUNT_JSON`에 JSON 전체를 환경변수로 입력할 수 있습니다. 두 값 중 하나만 사용합니다.

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
backend\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8001
```

백엔드 확인: `http://127.0.0.1:8001/health`, Swagger: `http://127.0.0.1:8001/docs`

다른 터미널에서 프론트엔드를 빌드하고 실행합니다. Node.js 20 이상이면 `--env-file`로 루트 `.env`를 빌드에 적용할 수 있습니다.

```powershell
cd frontend
npm ci
node --env-file=../.env build.mjs
npm run dev
```

프론트엔드 주소: `http://127.0.0.1:5500`

프론트엔드는 순수 HTML/CSS/JavaScript입니다. esbuild는 Firebase 인증 모듈을 묶고 Vercel 환경변수를 정적 `config.js`에 넣는 용도로만 사용합니다. 프론트엔드 환경변수를 변경한 후에는 다시 빌드해야 합니다.

## 100개 이상 테스트 데이터

[backend/seed_data.py](backend/seed_data.py)는 오늘을 기준으로 120일치 **가상 독서 기록**을 생성합니다. 실제 독서 기록이 아니라 과제용 시연 데이터임을 명시해 사용하세요.

```powershell
backend\.venv\Scripts\python.exe backend\seed_data.py
```

위 명령은 개수와 기간만 미리 보여줍니다. 앱에서 익명 로그인이 완료된 뒤 오른쪽 위 `나` 버튼을 누르면 본인 UID가 복사됩니다. 해당 브라우저의 기록으로 넣을 때만 다음 명령을 실행합니다.

```powershell
backend\.venv\Scripts\python.exe backend\seed_data.py --uid "복사한_UID" --apply
```

기존 `sample-날짜` 문서는 유지하며, 누락된 예시 기록만 추가합니다. 입력 후 앱을 새로고침하면 summary와 그래프에 반영됩니다.

## 테스트

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

14개 자동 테스트는 빈 데이터, 상승 추세, 120개 시계열 데이터, 입력 검증, 필수 API 경로, 토큰과 UID 사용, 기록 CRUD·대화 저장/불러오기/삭제의 모의 동작, AI 요약 주입·자동 저장을 확인합니다. Firebase·OpenAI 연동과 실제 브라우저 동작은 계정과 키가 준비된 뒤 추가 확인해야 합니다.

## 배포

### Render 백엔드

GitHub 저장소를 연결하고 루트의 [render.yaml](render.yaml) Blueprint를 사용하거나 Web Service에 다음을 입력합니다.

```text
Build: pip install -r backend/requirements.txt
Start: uvicorn main:app --app-dir backend --host 0.0.0.0 --port $PORT
```

Render 환경변수: `OPENAI_API_KEY`, `OPENAI_MODEL`, `FIREBASE_SERVICE_ACCOUNT_JSON`, `ALLOWED_ORIGINS`(Vercel 도메인). 서비스 계정 JSON은 비밀 환경변수에 저장합니다. 배포 후 `/health`와 `/docs`를 확인합니다. 무료 티어를 쓰는 경우 첫 요청에 시간이 걸릴 수 있어 프론트엔드에 안내 문구가 있습니다.

### Vercel 프론트엔드

같은 GitHub 저장소를 연결하고 루트의 [vercel.json](vercel.json)을 사용합니다. `API_BASE_URL`에 Render API 주소를 입력하고, `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, `FIREBASE_PROJECT_ID`, `FIREBASE_STORAGE_BUCKET`, `FIREBASE_MESSAGING_SENDER_ID`, `FIREBASE_APP_ID`를 Firebase Web 앱 설정값으로 입력합니다. 환경변수 수정 시 다시 빌드해 배포합니다.

Vercel 도메인을 Firebase Authentication의 승인된 도메인과 Render의 `ALLOWED_ORIGINS`에 추가합니다. Firestore에는 [firestore.rules](firestore.rules) 내용을 반영합니다.

## 배포 URL

| 항목 | URL |
|---|---|
| 프론트엔드 | 배포 후 입력 |
| 백엔드 API | 배포 후 입력 |
| Swagger UI | 배포 후 입력 |

## 제출 스크린샷

실제 Firebase·OpenAI 연동과 배포 확인 후 다음 3장을 촬영해 README에 첨부합니다.

1. 데이터 요약과 질문·AI 답변이 함께 보이는 채팅 화면
2. 독서 기록 추가 또는 수정·삭제 결과가 보이는 데이터 관리 화면
3. 이전 대화를 선택해 메시지를 다시 표시한 화면

현재 문서에는 확인되지 않은 배포 URL이나 스크린샷을 임의로 넣지 않았습니다.
