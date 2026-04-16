"""
Persona Interview Chatbot — FastAPI Backend

페르소나 기반 면접 연습 서버
- 대화: Claude Haiku + Tool Calling (save_answer 자동 호출)
- 최종 피드백: Claude Sonnet (구조화 데이터 기반 종합 리포트)
- DB: PostgreSQL (Docker) / SQLite (로컬 fallback)
"""

import json
import os
import uuid
import re
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from anthropic import Anthropic

from database import SessionLocal, create_tables
from db_models import SessionRecord, MessageRecord, AnswerRecord
from tools import TOOLS
from models import (
    InterviewStartRequest,
    InterviewStartResponse,
    AnswerRequest,
    InterviewResultsResponse,
    AnswerScore,
    ResetRequest,
)
from personas import (
    get_persona, get_all_personas, get_system_prompt,
    get_persona_questions, get_persona_question_by_id, get_persona_question_count,
)
from questions import get_all_questions

load_dotenv()

app = FastAPI(
    title="Persona Interview Chatbot",
    description="페르소나 기반 면접 연습 API (Tool Calling + 모델 분리)",
    version="3.0.0"
)

create_tables()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Anthropic()
MODEL_CHAT   = "claude-haiku-4-5-20251001"  # 대화: 빠르고 저렴
MODEL_REPORT = "claude-sonnet-4-5"           # 최종 피드백: 정확하고 깊음
MAX_MESSAGES = 20


# ============================================================
# 콘텐츠 직렬화 헬퍼
# Tool Calling 사용 시 assistant content가 문자열이 아닌 블록 리스트가 됨.
# DB 저장/로드 시 JSON 직렬화로 통일.
# ============================================================

def serialize_content(content: Any) -> str:
    """SDK 블록 객체 또는 문자열 → DB 저장용 문자열"""
    if isinstance(content, str):
        return content
    # 블록 리스트 (tool_use, text 등)
    blocks = []
    for block in content:
        if hasattr(block, "model_dump"):
            blocks.append(block.model_dump())
        elif isinstance(block, dict):
            blocks.append(block)
    return json.dumps(blocks, ensure_ascii=False)


def deserialize_content(content_str: str) -> Any:
    """DB 저장된 문자열 → Claude API 메시지 content"""
    try:
        parsed = json.loads(content_str)
        if isinstance(parsed, list):
            return parsed  # 블록 리스트
    except (json.JSONDecodeError, TypeError):
        pass
    return content_str  # 일반 텍스트


# ============================================================
# Health Check
# ============================================================

@app.get("/")
async def root():
    return {
        "status": "ok",
        "version": "3.0.0",
        "models": {"chat": MODEL_CHAT, "report": MODEL_REPORT},
    }


# ============================================================
# 페르소나 / 질문 API
# ============================================================

@app.get("/api/personas")
async def get_personas():
    personas = get_all_personas()
    return {"personas": personas, "count": len(personas)}


@app.get("/api/questions")
async def get_questions(lang: str = "ko"):
    questions = get_all_questions(lang)
    return {"questions": questions, "total": len(questions), "lang": lang}


# ============================================================
# 면접 세션 API
# ============================================================

@app.post("/api/interview/start")
async def start_interview(request: InterviewStartRequest) -> InterviewStartResponse:
    """면접 세션 시작 — DB에 세션 생성"""
    persona = get_persona(request.persona)
    if not persona:
        raise HTTPException(status_code=400, detail=f"Invalid persona: {request.persona}")

    session_id = request.session_id or str(uuid.uuid4())
    lang = request.lang or "ko"

    db = SessionLocal()
    try:
        existing = db.query(SessionRecord).filter_by(session_id=session_id).first()
        if existing:
            db.delete(existing)
            db.commit()
        db.add(SessionRecord(session_id=session_id, persona=request.persona, lang=lang))
        db.commit()
    finally:
        db.close()

    first_question = get_persona_question_by_id(request.persona, 1, lang)
    if not first_question:
        raise HTTPException(status_code=500, detail="Question not found")

    return InterviewStartResponse(
        session_id=session_id,
        persona=request.persona,
        status="ready",
        first_question=first_question["question"],
        questions=get_persona_questions(request.persona, lang),
    )


@app.post("/api/interview/answer")
async def answer_question(request: AnswerRequest):
    """
    사용자 답변 제출 — Haiku + Tool Calling + SSE 스트리밍

    흐름:
    1. DB에서 세션 + 대화 히스토리 로드
    2. Haiku 비스트리밍 호출 (tool_use 추출)
       → save_answer() 자동 호출 → DB에 구조화 저장
    3. tool_result 메시지 추가 후 Haiku 스트리밍 (실제 피드백 텍스트)
    """
    # ── DB 로드 ──
    db = SessionLocal()
    try:
        session_row = db.query(SessionRecord).filter_by(session_id=request.session_id).first()
        if not session_row:
            raise HTTPException(status_code=404, detail="Session not found")

        persona_id = session_row.persona
        lang = session_row.lang

        question = get_persona_question_by_id(persona_id, request.question_id, lang)
        if not question:
            raise HTTPException(status_code=400, detail="Question not found")

        message_rows = (
            db.query(MessageRecord)
            .filter_by(session_id=request.session_id)
            .order_by(MessageRecord.id)
            .all()
        )
        messages = [
            {"role": m.role, "content": deserialize_content(m.content)}
            for m in message_rows
        ]
    finally:
        db.close()

    # 토큰 한도 방어
    if len(messages) > MAX_MESSAGES:
        messages = messages[-MAX_MESSAGES:]

    system_prompt = get_system_prompt(persona_id)
    user_message_content = (
        f"[질문] {question['question']}\n\n"
        f"[답변] {request.answer}"
    )

    async def event_generator():
        try:
            # ── 1단계: Haiku 비스트리밍 — Tool Calling ──
            call_messages = messages + [{"role": "user", "content": user_message_content}]

            response = client.messages.create(
                model=MODEL_CHAT,
                system=system_prompt,
                messages=call_messages,
                tools=TOOLS,
                max_tokens=2048,
            )

            assistant_text = ""
            tool_use_block = None

            for block in response.content:
                if block.type == "text":
                    assistant_text += block.text
                elif block.type == "tool_use" and block.name == "save_answer":
                    tool_use_block = block

            # ── 2단계: Tool 결과 처리 → DB 저장 ──
            if tool_use_block:
                tool_input = tool_use_block.input
                score = int(tool_input.get("score", 5))
                score = min(10, max(1, score))

                write_db = SessionLocal()
                try:
                    # 유저 메시지 저장
                    write_db.add(MessageRecord(
                        session_id=request.session_id,
                        role="user",
                        content=user_message_content,
                    ))
                    # assistant 메시지 저장 (tool_use 블록 포함)
                    write_db.add(MessageRecord(
                        session_id=request.session_id,
                        role="assistant",
                        content=serialize_content(response.content),
                    ))
                    # tool_result 메시지 저장
                    tool_result_content = json.dumps([{
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": "保存しました",
                    }], ensure_ascii=False)
                    write_db.add(MessageRecord(
                        session_id=request.session_id,
                        role="user",
                        content=tool_result_content,
                    ))
                    # 구조화 답변 저장
                    write_db.add(AnswerRecord(
                        session_id=request.session_id,
                        question_id=request.question_id,
                        question=question["question"],
                        answer=request.answer,
                        score=score,
                        answer_summary=tool_input.get("answer_summary", ""),
                        keywords=json.dumps(tool_input.get("keywords", []), ensure_ascii=False),
                        red_flags=json.dumps(tool_input.get("red_flags", []), ensure_ascii=False),
                        input_tokens=response.usage.input_tokens,
                        output_tokens=response.usage.output_tokens,
                    ))
                    write_db.commit()

                    # tool_use 저장 완료 이벤트
                    yield f'data: {json.dumps({"tool_saved": True, "score": score})}\n\n'
                finally:
                    write_db.close()

                # ── 3단계: tool_result 포함한 히스토리로 Haiku 스트리밍 ──
                stream_messages = call_messages + [
                    {"role": "assistant", "content": response.content},
                    {
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_use_block.id,
                            "content": "保存しました",
                        }]
                    },
                ]

                full_feedback = ""
                with client.messages.stream(
                    model=MODEL_CHAT,
                    system=system_prompt,
                    messages=stream_messages,
                    max_tokens=2048,
                ) as stream:
                    for text in stream.text_stream:
                        full_feedback += text
                        yield f'data: {json.dumps({"text": text})}\n\n'

                    final = stream.get_final_message()

                # 피드백 텍스트를 AnswerRecord에 업데이트
                update_db = SessionLocal()
                try:
                    answer_row = (
                        update_db.query(AnswerRecord)
                        .filter_by(session_id=request.session_id, question_id=request.question_id)
                        .order_by(AnswerRecord.id.desc())
                        .first()
                    )
                    if answer_row:
                        answer_row.feedback = full_feedback
                        answer_row.output_tokens = final.usage.output_tokens
                        update_db.commit()
                    # assistant 피드백 메시지 저장
                    update_db.add(MessageRecord(
                        session_id=request.session_id,
                        role="assistant",
                        content=full_feedback,
                    ))
                    update_db.commit()
                finally:
                    update_db.close()

                yield f'data: {json.dumps({"done": True, "score": score})}\n\n'

            else:
                # Tool 미호출 — 텍스트 스트리밍 후 fallback으로 AnswerRecord 저장
                for char in assistant_text:
                    yield f'data: {json.dumps({"text": char})}\n\n'

                fallback_score = extract_score(assistant_text)

                save_db = SessionLocal()
                try:
                    save_db.add(MessageRecord(
                        session_id=request.session_id,
                        role="user",
                        content=user_message_content,
                    ))
                    save_db.add(MessageRecord(
                        session_id=request.session_id,
                        role="assistant",
                        content=assistant_text,
                    ))
                    # Tool 없이도 AnswerRecord 반드시 저장 (결과 페이지 정상화)
                    save_db.add(AnswerRecord(
                        session_id=request.session_id,
                        question_id=request.question_id,
                        question=question["question"],
                        answer=request.answer,
                        score=fallback_score,
                        feedback=assistant_text,
                        input_tokens=response.usage.input_tokens,
                        output_tokens=response.usage.output_tokens,
                    ))
                    save_db.commit()
                finally:
                    save_db.close()

                yield f'data: {json.dumps({"done": True, "score": fallback_score})}\n\n'

        except Exception as e:
            yield f'data: {json.dumps({"error": str(e)})}\n\n'

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/interview/feedback/{session_id}")
async def generate_feedback(session_id: str):
    """
    면접 종료 후 Sonnet으로 종합 피드백 리포트 생성 — SSE 스트리밍

    Tool Calling으로 쌓인 구조화 데이터(answer_summary, keywords, red_flags)를
    Sonnet에 전달해 페르소나별 심층 분석 리포트 생성.
    """
    db = SessionLocal()
    try:
        session_row = db.query(SessionRecord).filter_by(session_id=session_id).first()
        if not session_row:
            raise HTTPException(status_code=404, detail="Session not found")

        answer_rows = (
            db.query(AnswerRecord)
            .filter_by(session_id=session_id)
            .order_by(AnswerRecord.id)
            .all()
        )

        if not answer_rows:
            raise HTTPException(status_code=400, detail="回答データがありません")

        persona_id = session_row.persona
        persona = get_persona(persona_id)

        # 구조화 데이터 조립
        evaluated = [
            {
                "question_index": i + 1,
                "question": a.question,
                "answer_summary": a.answer_summary or "",
                "keywords": json.loads(a.keywords or "[]"),
                "score": a.score,
                "red_flags": json.loads(a.red_flags or "[]"),
            }
            for i, a in enumerate(answer_rows)
        ]

        avg_score = sum(a.score for a in answer_rows) / len(answer_rows)
        eval_criteria = persona.get("eval_criteria", [])
    finally:
        db.close()

    prompt = f"""あなたは採用コンサルタントです。
以下の面接データをもとに、候補者への構造化フィードバックを日本語で生成してください。

## ペルソナ: {persona["name"]}
## 評価軸: {", ".join(eval_criteria)}
## 平均スコア: {avg_score:.1f}/10

## 面接データ
{json.dumps(evaluated, ensure_ascii=False, indent=2)}

## 出力形式（必ずこの形式で）

### 総合評価: {avg_score:.1f}/10

### 強み
1.
2.
3.

### 改善点
1.
2.

### {persona["name"]}視点からの一言
...

### 次のステップ
...
"""

    def feedback_stream():
        with client.messages.stream(
            model=MODEL_REPORT,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
        ) as stream:
            for text in stream.text_stream:
                yield f'data: {json.dumps({"text": text})}\n\n'
        yield f'data: {json.dumps({"done": True})}\n\n'

    return StreamingResponse(feedback_stream(), media_type="text/event-stream")


@app.get("/api/interview/results/{session_id}")
async def get_results(session_id: str) -> InterviewResultsResponse:
    """면접 세션 결과 조회"""
    db = SessionLocal()
    try:
        session_row = db.query(SessionRecord).filter_by(session_id=session_id).first()
        if not session_row:
            raise HTTPException(status_code=404, detail="Session not found")

        answer_rows = (
            db.query(AnswerRecord)
            .filter_by(session_id=session_id)
            .order_by(AnswerRecord.id)
            .all()
        )

        total_questions = get_persona_question_count(session_row.persona)
        avg_score = sum(a.score for a in answer_rows) / len(answer_rows) if answer_rows else 0.0

        answer_scores = [
            AnswerScore(
                question_id=a.question_id,
                question=a.question,
                score=a.score,
                feedback=a.feedback or "",
            )
            for a in answer_rows
        ]

        return InterviewResultsResponse(
            session_id=session_id,
            persona=session_row.persona,
            total_questions=total_questions,
            answered_count=len(answer_rows),
            accuracy_rate=avg_score / 10.0,
            answers=answer_scores,
        )
    finally:
        db.close()


@app.post("/api/interview/reset")
async def reset_session(request: ResetRequest):
    """세션 초기화"""
    db = SessionLocal()
    try:
        session_row = db.query(SessionRecord).filter_by(session_id=request.session_id).first()
        if session_row:
            db.delete(session_row)
            db.commit()
    finally:
        db.close()
    return {"status": "ok"}


# ============================================================
# 앱 실행
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
