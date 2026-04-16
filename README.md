# Persona Interview Chatbot

LLM의 System Prompt로 다양한 페르소나를 구현하고,  
페르소나별 맞춤 면접 질문에 AI가 실시간 평가를 제공하는 면접 연습 애플리케이션.

---

## 프로젝트 개요

취업 준비 과정에서 피드백을 줄 수 있는 상대가 없다는 문제에서 출발.  
"왜 AI로 실제 면접관처럼 피드백을 줄 수 없을까?"라는 질문에서 시작해,  
**인사담당자 / 기술담당자 / 임원** 3종 페르소나 기반 AI 면접관을 구현.

### 핵심 학습 목표

- LLM의 System Prompt로 페르소나(역할)를 설계하는 방법
- SSE(Server-Sent Events)로 AI 응답을 토큰 단위로 실시간 스트리밍하는 방법
- Tool Calling으로 비정형 LLM 응답을 구조화된 데이터로 추출하는 방법
- Haiku(대화) / Sonnet(분석)으로 역할에 따라 모델을 분리해 비용과 품질을 최적화하는 방법

---

## 기술 스택

| 계층 | 기술 |
|------|------|
| Backend | FastAPI, Uvicorn, Pydantic |
| Frontend | React 18, Vite |
| LLM | Anthropic Claude API |
| Streaming | SSE (Server-Sent Events) |
| DB | PostgreSQL (Docker) / SQLite (로컬 fallback) |
| ORM | SQLAlchemy 2.0 |
| Infrastructure | Docker, Docker Compose |

---

## 주요 흐름

### 1. 면접 대화 흐름 (Haiku + Tool Calling)

```
유저 답변 제출
    │
    ▼
Claude Haiku — 비스트리밍 호출 (tools=[save_answer])
    │
    ├─► text 블록       → 임시 보관
    └─► tool_use 블록   → save_answer() 자동 호출
                              │
                              ▼
                         DB 저장 (구조화 데이터)
                         answer_summary / keywords
                         score / red_flags
                              │
                              ▼
                         tool_result 메시지 추가
                              │
                              ▼
Claude Haiku — 스트리밍 호출
    │
    ▼
실시간 피드백 텍스트 → 브라우저 출력 (SSE)
```

### 2. SSE 스트리밍 흐름

```
FastAPI (StreamingResponse + async generator)
    │ data: {"text": "토큰"}\n\n
    ▼
Fetch API + ReadableStream (프론트엔드)
    │ TextDecoder → buffer → \n\n 기준 이벤트 분리
    ▼
React setResponse(prev => prev + text)
    │
    ▼
화면에 타이핑 효과로 실시간 렌더링
```

### 3. 최종 피드백 리포트 흐름

```
면접 종료
    │
    ▼
DB에서 구조화 데이터 조회
(answer_summary, keywords, score, red_flags × N문항)
    │
    ▼
Claude Sonnet — 종합 피드백 리포트 생성
(강점 / 개선점 / 페르소나 시점 총평 / 다음 스텝)
    │
    ▼
SSE 스트리밍으로 리포트 출력
```

---

## 설계 포인트

### 1. System Prompt로 페르소나 구현

별도 파인튜닝 없이 System Prompt만으로 3종 면접관을 구현.  
각 페르소나는 **Role / Tone / Scope / Rules** 4요소로 설계.

```python
# personas.py
"hr": {
    "system": (
        # Role: 역할 정의
        "당신은 경험 많은 기업의 인사담당자입니다."
        # Tone: 말투
        "따뜻하면서도 전문적인 톤을 사용합니다."
        # Scope: 평가 범위
        "성실성, 경험, 문화 핏, 협업 능력을 중점 평가합니다."
        # Rules: 출력 규칙
        "피드백은 [문화적합성] / [커뮤니케이션] / [성장의지] 3축으로 구조화합니다."
    ),
    "eval_criteria": ["문화적합성", "커뮤니케이션", "성장의지"],
    "questions": [...]   # 페르소나별 독립 질문
}
```

| 페르소나 | 평가 축 | 질문 포커스 |
|----------|---------|------------|
| 인사담당자 | 문화적합성 / 커뮤니케이션 / 성장의지 | 경험, 팀워크, 동기 |
| 기술담당자 | 기술깊이 / 문제해결력 / 설계사고 | 기술스택, 설계, 품질 |
| 임원 | 전략적사고 / 리더십 / 비전명확성 | 리더십, 비전, 의사결정 |

### 2. Tool Calling으로 구조화된 평가 데이터 추출

LLM의 자유형 텍스트 응답에서 평가 데이터를 안정적으로 추출하기 위해 Tool Calling 사용.  
단순 텍스트 파싱(`정규식`)보다 구조적으로 신뢰할 수 있는 방식.

```python
# tools.py — save_answer 도구 정의
{
    "name": "save_answer",
    "input_schema": {
        "properties": {
            "answer_summary": "1~2문 요약",
            "keywords":       "핵심 키워드 배열 (최대 5개)",
            "score":          "평가 점수 (1~10)",
            "red_flags":      "우려점 배열"
        }
    }
}
```

### 3. 모델 역할 분리 (비용 최적화)

| 역할 | 모델 | 이유 |
|------|------|------|
| 대화 + Tool Calling | `claude-haiku-4-5` | 빠름, 저렴, 반복 호출 |
| 최종 피드백 리포트 | `claude-sonnet-4-5` | 정확, 깊은 분석 (1회) |

### 4. Fetch + ReadableStream (XHR 대신)

POST 요청으로 SSE를 처리해야 해서 `EventSource`(GET 전용)를 사용할 수 없음.  
XHR `onprogress` 방식은 누적 텍스트 재처리 문제가 있어 현대 표준 방식으로 교체.

```javascript
// 현대적 표준 방식
const res = await fetch('/api/interview/answer', { method: 'POST', body: ... })
const reader = res.body.getReader()
const decoder = new TextDecoder()
let buffer = ''

while (true) {
  const { done, value } = await reader.read()
  if (done) break
  buffer += decoder.decode(value, { stream: true })
  const events = buffer.split('\n\n')
  buffer = events.pop()   // 미완성 청크 보존
  for (const event of events) { /* 파싱 */ }
}
```

### 5. DB 영속화 (PostgreSQL / SQLite)

환경변수 `DATABASE_URL` 하나로 SQLite(로컬) ↔ PostgreSQL(프로덕션) 자동 전환.  
SQLAlchemy cascade 설정으로 세션 삭제 시 관련 메시지/답변 자동 삭제.

```
sessions  ─┬─► messages  (대화 히스토리)
            └─► answers   (구조화 평가 데이터)
```

### 6. 토큰 한도 방어

대화가 길어지면 Claude API 컨텍스트 한도 초과 방지를 위해 최근 N개 메시지만 전송.

```python
MAX_MESSAGES = 20
if len(messages) > MAX_MESSAGES:
    messages = messages[-MAX_MESSAGES:]
```

---

## 디렉토리 구조

```
Persona/
├── docker-compose.yml          # PostgreSQL + pgAdmin
│
├── backend/
│   ├── main.py                 # FastAPI 엔드포인트
│   ├── personas.py             # 페르소나 정의 (System Prompt + 질문 + 평가 기준)
│   ├── tools.py                # Tool Calling 정의 (save_answer)
│   ├── questions.py            # 공통 질문 (하위 호환)
│   ├── models.py               # Pydantic 요청/응답 모델
│   ├── database.py             # SQLAlchemy 엔진 설정
│   ├── db_models.py            # ORM 테이블 (sessions / messages / answers)
│   ├── requirements.txt
│   └── .env                    # ANTHROPIC_API_KEY, DATABASE_URL
│
└── frontend/
    └── src/
        ├── App.jsx
        └── components/
            ├── PersonaSelector.jsx
            ├── InterviewUI.jsx     # Fetch + ReadableStream SSE
            ├── Results.jsx
            └── LangToggle.jsx
```

---

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/personas` | 페르소나 목록 |
| POST | `/api/interview/start` | 세션 시작 (페르소나별 질문 포함) |
| POST | `/api/interview/answer` | 답변 제출 → SSE 스트리밍 평가 |
| GET | `/api/interview/feedback/{id}` | Sonnet 종합 리포트 (SSE) |
| GET | `/api/interview/results/{id}` | 세션 결과 조회 |
| POST | `/api/interview/reset` | 세션 초기화 |

---

## 실행 방법

```bash
# 1. DB 실행 (Docker)
docker compose up -d

# 2. 백엔드
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 3. 프론트엔드
cd frontend
npm install
npm run dev
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- pgAdmin: `http://localhost:5050` (admin@persona.dev / admin)

---

## 개발 기간 · 인원

2026.04 ~ 현재 / 1명
