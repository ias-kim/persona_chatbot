# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**페르소나 면접 챗봇 (Interview Persona Chatbot)**

LLM의 System Prompt를 통해 다양한 페르소나를 구현하고, 면접 준비 질문을 페르소나별로 대응하는 애플리케이션입니다.

### Key Concepts

1. **페르소나 (Persona)**
   - AI에게 부여하는 역할 설정 (Role)
   - System Prompt의 4가지 요소: Role, Tone, Scope, Rules
   - 동일한 LLM도 페르소나에 따라 응답 스타일이 완전히 달라짐

2. **SSE (Server-Sent Events)**
   - 서버가 클라이언트에게 실시간으로 한 방향 데이터 스트리밍
   - Claude API의 스트리밍 응답을 토큰 단위로 브라우저에 전달

3. **3가지 면접 페르소나**
   - **인사담당자** (HR): 자질, 경험, 가치관 중심
   - **기술담당자** (Technical): 기술 스킬, 문제 해결 능력 중심
   - **임원** (Executive): 전략, 리더십, 비전 중심

---

## Tech Stack

| 계층 | 기술 |
|------|------|
| Backend | FastAPI, Uvicorn, Pydantic |
| Frontend | React 18+, Axios/Fetch |
| LLM | Anthropic Claude API (Sonnet 4) |
| Streaming | SSE (Server-Sent Events) |
| Python Version | 3.10+ |

---

## Directory Structure

```
Persona/
├── backend/
│   ├── main.py              # FastAPI 애플리케이션 진입점
│   ├── personas.py          # 페르소나 정의 (System Prompt)
│   ├── questions.py         # 면접 질문 리스트
│   ├── models.py            # Pydantic 데이터 모델
│   ├── requirements.txt      # 파이썬 의존성
│   └── .env                 # 환경변수 (ANTHROPIC_API_KEY)
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── PersonaSelector.jsx    # 페르소나 선택
│   │   │   ├── InterviewUI.jsx        # 면접 인터페이스
│   │   │   ├── QuestionList.jsx       # 질문 리스트
│   │   │   └── Results.jsx            # 결과 및 통계
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── index.js
│   ├── package.json
│   └── .env                 # REACT_APP_API_URL=http://localhost:8000
│
└── CLAUDE.md
```

---

## Quick Start

### 환경 설정

1. **백엔드 의존성 설치**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **환경변수 설정**
   ```bash
   # backend/.env
   ANTHROPIC_API_KEY=sk-ant-...
   ```

3. **프론트엔드 의존성 설치**
   ```bash
   cd frontend
   npm install
   ```

### 개발 서버 실행

**터미널 1 — 백엔드**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**터미널 2 — 프론트엔드**
```bash
cd frontend
npm start
```

서버가 실행되면:
- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:3000` (자동 오픈)

---

## Architecture

### 백엔드 핵심 흐름

```
클라이언트 (React)
    │
    │ POST /api/interview/start
    │ {"persona": "hr", "session_id": "..."}
    ▼
FastAPI 엔드포인트
    │
    ├─► 질문 리스트 조회
    │
    ├─► 페르소나 System Prompt 로드
    │
    └─► Claude API 스트리밍 호출
        (messages + system prompt)
    │
    ▼
SSE 응답 (토큰 단위 스트리밍)
    │
    ├─► data: {"text": "안녕"}\n\n
    ├─► data: {"text": "하세요"}\n\n
    └─► data: {"done": true, "tokens": ...}\n\n
    │
    ▼
클라이언트 (EventSource로 수신)
```

### 페르소나 구현

System Prompt에 4가지 요소를 명시:

```python
# personas.py 예시
PERSONAS = {
    "hr": {
        "name": "인사담당자",
        "system": (
            # Role
            "당신은 경험 많은 HR 담당자입니다. "
            # Tone
            "전문적이면서도 따뜻한 톤으로 대화합니다. "
            # Scope
            "후보자의 경험, 가치관, 팀 핏을 중점으로 평가합니다. "
            # Rules
            "구체적인 예시를 들도록 유도하며, "
            "문화적 적응력과 팀워크를 강조합니다."
        )
    }
}
```

### 질문 리스트

`questions.py`에 다음 구조로 정의:

```python
QUESTIONS = [
    {
        "id": 1,
        "question": "자신을 소개해주세요.",
        "difficulty": "easy",
        "category": "self-intro"
    },
    ...
]
```

---

## API Endpoints

### 1. `GET /api/personas`
모든 페르소나 메타데이터 조회

**Response:**
```json
{
  "personas": [
    {
      "id": "hr",
      "name": "인사담당자",
      "description": "자질, 경험, 가치관 중심"
    }
  ]
}
```

---

### 2. `GET /api/questions`
면접 질문 리스트 조회

**Response:**
```json
{
  "questions": [
    {
      "id": 1,
      "question": "자신을 소개해주세요.",
      "difficulty": "easy"
    }
  ],
  "total": 18
}
```

---

### 3. `POST /api/interview/start`
면접 세션 시작 (새 conversation 생성)

**Request:**
```json
{
  "persona": "hr",
  "session_id": "user-123-001"
}
```

**Response:**
```json
{
  "session_id": "user-123-001",
  "persona": "hr",
  "status": "ready",
  "first_question": "자신을 소개해주세요."
}
```

---

### 4. `POST /api/interview/answer` — SSE 스트리밍
사용자의 답변에 대한 AI 평가 (스트리밍)

**Request:**
```json
{
  "session_id": "user-123-001",
  "question_id": 1,
  "answer": "저는 5년 경험의 백엔드 개발자입니다..."
}
```

**Response (SSE):**
```
data: {"text": "좋은"}\n\n
data: {"text": " 답변이네요"}\n\n
data: {"text": "..."}\n\n
data: {"done": true, "score": 8, "feedback": "..."}
```

---

### 5. `GET /api/interview/results/{session_id}`
면접 세션의 최종 결과

**Response:**
```json
{
  "session_id": "user-123-001",
  "persona": "hr",
  "answered": 5,
  "total": 18,
  "accuracy": 0.55,
  "answers": [
    {
      "question_id": 1,
      "score": 8,
      "feedback": "..."
    }
  ]
}
```

---

### 6. `POST /api/interview/reset`
세션 초기화

**Request:**
```json
{
  "session_id": "user-123-001"
}
```

---

## Development

### 테스트 (Optional)

```bash
# 백엔드 테스트 (pytest)
cd backend
pytest tests/

# 프론트엔드 테스트 (Jest)
cd frontend
npm test
```

### 로컬 API 테스트

```bash
# 페르소나 목록 조회
curl http://localhost:8000/api/personas

# 질문 목록 조회
curl http://localhost:8000/api/questions

# SSE 스트리밍 테스트 (curl)
curl -X POST http://localhost:8000/api/interview/answer \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","question_id":1,"answer":"sample"}'
```

---

## Key Implementation Notes

### 1. SSE + EventSource 패턴

**백엔드:**
```python
from fastapi.responses import StreamingResponse

async def stream_interview_response(session_id, question_id, answer):
    async def event_generator():
        with client.messages.stream(...) as stream:
            for text in stream.text_stream:
                yield f'data: {json.dumps({"text": text})}\n\n'
            yield f'data: {json.dumps({"done": True})}\n\n'
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**프론트엔드:**
```javascript
const eventSource = new EventSource('/api/interview/answer');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.done) {
    eventSource.close();
  } else {
    setResponse(prev => prev + data.text);
  }
};
```

### 2. 페르소나별 System Prompt 분리

각 페르소나는 독립적인 System Prompt를 가져야 합니다.
Claude API 호출 시 `system` 파라미터에 페르소나의 System Prompt를 전달하면,
동일한 질문도 페르소나에 따라 다르게 평가합니다.

### 3. 세션 관리

간단한 구현: 메모리 저장 (in-process dictionary)
```python
conversations: Dict[str, List[MessageParam]] = {}
```

확장성이 필요하면 Redis/DB로 마이그레이션합니다.

### 4. CORS 설정

React (localhost:3000)에서 FastAPI (localhost:8000) 요청 허용:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Important Design Decisions

| 결정사항 | 이유 |
|---------|------|
| **FastAPI** | 비동기 지원, SSE 스트리밍에 최적화 |
| **SSE (WebSocket ✗)** | 단방향 스트리밍으로 충분, 더 간단 |
| **메모리 세션** | MVP 구현 단계, 나중에 DB로 확장 |
| **React Hooks** | 상태 관리 간단 (Redux ✗) |
| **System Prompt로 페르소나** | 추가 모델 없이 구현 가능, 비용 효율적 |

---

## Future Enhancements

- [ ] 질문 리스트를 DB/JSON으로 관리
- [ ] 사용자 계정 및 결과 저장 (PostgreSQL)
- [ ] 더 많은 페르소나 추가 (예: 스타트업 창업자, 메니토)
- [ ] 음성 입력 지원 (Web Speech API)
- [ ] 결과 PDF 내보내기
- [ ] 모의 면접 비디오 녹화

---

## Useful Commands

```bash
# 백엔드
cd backend
pip install -r requirements.txt          # 의존성 설치
uvicorn main:app --reload --port 8000   # 개발 서버
python -m pip freeze > requirements.txt  # 의존성 업데이트

# 프론트엔드
cd frontend
npm install                              # 의존성 설치
npm start                                # 개발 서버
npm run build                            # 프로덕션 빌드
```

---

## Language

모든 개발은 **한국어 주석/로그**를 사용합니다.
API 응답은 한국어로 제공하며, 코드는 영문 변수명을 사용합니다.
