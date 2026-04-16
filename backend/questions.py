"""
면접 질문 리스트 (18개) — 한국어 / 일본어 지원
"""

QUESTIONS = [
    {
        "id": 1,
        "ko": "자신을 소개해주세요.",
        "ja": "自己紹介をお願いします。",
        "difficulty": "easy",
        "category": "self-intro"
    },
    {
        "id": 2,
        "ko": "주변 사람들은 당신을 어떤 사람이라고 말하나요?",
        "ja": "周りからはどのような人だと言われますか。",
        "difficulty": "easy",
        "category": "personality"
    },
    {
        "id": 3,
        "ko": "자신의 강점을 PR해주세요.",
        "ja": "自己PRをお願いします。",
        "difficulty": "medium",
        "category": "strength"
    },
    {
        "id": 4,
        "ko": "당신의 강점은 무엇인가요?",
        "ja": "あなたの強みは何ですか。",
        "difficulty": "easy",
        "category": "strength"
    },
    {
        "id": 5,
        "ko": "당신의 약점은 무엇인가요?",
        "ja": "あなたの弱みは何ですか。",
        "difficulty": "medium",
        "category": "weakness"
    },
    {
        "id": 6,
        "ko": "인생에서 가장 열심히 한 일은 무엇인가요?",
        "ja": "人生で最も頑張ったことは何ですか。",
        "difficulty": "medium",
        "category": "experience"
    },
    {
        "id": 7,
        "ko": "어떤 엔지니어가 되고 싶은가요?",
        "ja": "どんなエンジニアになりたいですか。",
        "difficulty": "medium",
        "category": "career-vision"
    },
    {
        "id": 8,
        "ko": "회사 선택의 기준을 말씀해주세요.",
        "ja": "会社選びの軸を教えてください。",
        "difficulty": "hard",
        "category": "company-criteria"
    },
    {
        "id": 9,
        "ko": "좌절한 경험이 있나요?",
        "ja": "挫折した経験はありますか。",
        "difficulty": "hard",
        "category": "failure-experience"
    },
    {
        "id": 10,
        "ko": "1년 후, 5년 후, 10년 후에 어떻게 되고 싶나요?",
        "ja": "1年後、5年後、10年後にどうなっていたいですか。",
        "difficulty": "hard",
        "category": "career-planning"
    },
    {
        "id": 11,
        "ko": "왜 이 대학/학부/전공을 선택했나요?",
        "ja": "なぜこの大学・学部・学科を選んだのですか。",
        "difficulty": "easy",
        "category": "education"
    },
    {
        "id": 12,
        "ko": "학생 시절에 가장 열심히 한 일은 무엇인가요?",
        "ja": "学生時代に最も力を入れたことは何ですか。",
        "difficulty": "medium",
        "category": "student-experience"
    },
    {
        "id": 13,
        "ko": "리더로서 어려웠던 점은 무엇인가요?",
        "ja": "リーダーとして難しかったことは何ですか。",
        "difficulty": "hard",
        "category": "leadership"
    },
    {
        "id": 14,
        "ko": "왜 엔지니어를 지망하고 있나요?",
        "ja": "なぜエンジニアを志望しているのですか。",
        "difficulty": "medium",
        "category": "motivation"
    },
    {
        "id": 15,
        "ko": "팀에서 당신의 역할은 무엇이었나요?",
        "ja": "チームでのあなたの役割は何でしたか。",
        "difficulty": "medium",
        "category": "teamwork"
    },
    {
        "id": 16,
        "ko": "왜 이 회사에 지원하게 되었나요?",
        "ja": "なぜ日本で就職したいのですか。",
        "difficulty": "hard",
        "category": "company-interest"
    },
    {
        "id": 17,
        "ko": "팀 개발에서 힘들었던 점은 무엇인가요?",
        "ja": "チーム開発で苦労したことは何ですか。",
        "difficulty": "hard",
        "category": "teamwork"
    },
    {
        "id": 18,
        "ko": "리더십을 발휘한 경험을 말씀해주세요.",
        "ja": "リーダーシップを発揮した経験を教えてください。",
        "difficulty": "hard",
        "category": "leadership"
    }
]


def get_all_questions(lang: str = "ko"):
    """언어별 질문 반환 (ko: 한국어, ja: 일본어)"""
    return [
        {
            "id": q["id"],
            "question": q.get(lang, q["ko"]),  # 없는 언어면 한국어 fallback
            "difficulty": q["difficulty"],
            "category": q["category"],
        }
        for q in QUESTIONS
    ]


def get_question_by_id(question_id: int, lang: str = "ko"):
    """ID로 특정 질문 조회"""
    for q in QUESTIONS:
        if q["id"] == question_id:
            return {
                "id": q["id"],
                "question": q.get(lang, q["ko"]),
                "difficulty": q["difficulty"],
                "category": q["category"],
            }
    return None


def get_question_count():
    """전체 질문 수"""
    return len(QUESTIONS)
