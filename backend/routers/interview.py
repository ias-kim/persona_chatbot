import json
import re
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from anthropic import Anthropic

from database import SessionLocal
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
    get_persona,
    get_system_prompt,
    get_persona_questions,
    get_persona_question_by_id,
    get_persona_question_count,
)

router = APIRouter(prefix="/api/interview", tags=["interview"])

client = Anthropic()
MODEL_CHAT   = "claude-haiku-4-5-20251001"
MODEL_REPORT = "claude-sonnet-4-5"
MAX_MESSAGES = 20


# ── 헬퍼 ──────────────────────────────────────────────────────

def serialize_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    blocks = []
    for block in content:
        if hasattr(block, "model_dump"):
            blocks.append(block.model_dump())
        elif isinstance(block, dict):
            blocks.append(block)
    return json.dumps(blocks, ensure_ascii=False)


def deserialize_content(content_str: str) -> Any:
    try:
        parsed = json.loads(content_str)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return content_str


def extract_score(text: str) -> int:
    """텍스트에서 1~10 점수 추출. 없으면 기본값 5 반환."""
    for pattern in [r'(\d+)\s*/\s*10', r'점수[:\s]+(\d+)', r'score[:\s]+(\d+)']:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return min(10, max(1, int(m.group(1))))
    return 5


# ── 엔드포인트 ─────────────────────────────────────────────────

@router.post("/start")
async def start_interview(request: InterviewStartRequest) -> InterviewStartResponse:
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


@router.post("/answer")
async def answer_question(request: AnswerRequest):
    """Haiku + Tool Calling + SSE 스트리밍"""
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

    if len(messages) > MAX_MESSAGES:
        messages = messages[-MAX_MESSAGES:]

    system_prompt = get_system_prompt(persona_id)
    user_message_content = f"[질문] {question['question']}\n\n[답변] {request.answer}"

    async def event_generator():
        try:
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

            if tool_use_block:
                tool_input = tool_use_block.input
                score = min(10, max(1, int(tool_input.get("score", 5))))

                write_db = SessionLocal()
                try:
                    write_db.add(MessageRecord(
                        session_id=request.session_id,
                        role="user",
                        content=user_message_content,
                    ))
                    write_db.add(MessageRecord(
                        session_id=request.session_id,
                        role="assistant",
                        content=serialize_content(response.content),
                    ))
                    tool_result_content = json.dumps([{
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": "저장완료",
                    }], ensure_ascii=False)
                    write_db.add(MessageRecord(
                        session_id=request.session_id,
                        role="user",
                        content=tool_result_content,
                    ))
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
                    yield f'data: {json.dumps({"tool_saved": True, "score": score})}\n\n'
                finally:
                    write_db.close()

                stream_messages = call_messages + [
                    {"role": "assistant", "content": response.content},
                    {
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_use_block.id,
                            "content": "저장완료",
                        }],
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
                # Tool 미호출 fallback
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


@router.get("/feedback/{session_id}")
async def generate_feedback(session_id: str):
    """Sonnet으로 종합 피드백 리포트 생성 — SSE 스트리밍"""
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
            raise HTTPException(status_code=400, detail="답변 데이터가 없습니다")

        persona_id = session_row.persona
        persona = get_persona(persona_id)

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

    prompt = f"""당신은 채용 컨설턴트입니다.
아래 면접 데이터를 바탕으로 지원자에게 구조화된 피드백을 한국어로 작성해주세요.

## 페르소나: {persona["name"]}
## 평가 기준: {", ".join(eval_criteria)}
## 평균 점수: {avg_score:.1f}/10

## 면접 데이터
{json.dumps(evaluated, ensure_ascii=False, indent=2)}

## 출력 형식 (반드시 이 형식으로)

### 종합 평가: {avg_score:.1f}/10

### 강점
1.
2.
3.

### 개선점
1.
2.

### {persona["name"]} 관점에서 한마디
...

### 다음 단계
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


@router.get("/results/{session_id}")
async def get_results(session_id: str) -> InterviewResultsResponse:
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

        return InterviewResultsResponse(
            session_id=session_id,
            persona=session_row.persona,
            total_questions=total_questions,
            answered_count=len(answer_rows),
            accuracy_rate=avg_score / 10.0,
            answers=[
                AnswerScore(
                    question_id=a.question_id,
                    question=a.question,
                    score=a.score,
                    feedback=a.feedback or "",
                )
                for a in answer_rows
            ],
        )
    finally:
        db.close()


@router.post("/reset")
async def reset_session(request: ResetRequest):
    db = SessionLocal()
    try:
        session_row = db.query(SessionRecord).filter_by(session_id=request.session_id).first()
        if session_row:
            db.delete(session_row)
            db.commit()
    finally:
        db.close()
    return {"status": "ok"}
