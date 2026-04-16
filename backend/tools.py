"""
Claude Tool Calling 정의

save_answer: 면접 답변을 구조화 저장하는 도구.
Haiku가 대화 중 자동으로 호출하여 평가 데이터를 일관된 형식으로 추출한다.
"""

TOOLS = [
    {
        "name": "save_answer",
        "description": (
            "候補者が質問に答えたとき、その内容を構造化して保存する。"
            "毎回の回答後に必ず呼び出すこと。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "今回の質問内容"
                },
                "answer_summary": {
                    "type": "string",
                    "description": "候補者の回答を1〜2文で要約"
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "回答から抽出した重要キーワード（最大5個）"
                },
                "score": {
                    "type": "number",
                    "description": "この回答への評価（1〜10）"
                },
                "red_flags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "懸念点があれば記録。なければ空配列"
                }
            },
            "required": ["question", "answer_summary", "score", "keywords", "red_flags"]
        }
    }
]
