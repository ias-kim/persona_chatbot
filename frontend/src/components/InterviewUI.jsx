import { useState } from 'react'
import './InterviewUI.css'

function InterviewUI({ persona, questions, sessionId, apiBaseUrl, onComplete }) {
  const [currentQuestionId, setCurrentQuestionId] = useState(1)
  const [answer, setAnswer] = useState('')
  const [response, setResponse] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isDone, setIsDone] = useState(false)
  const [score, setScore] = useState(null)
  const [answeredCount, setAnsweredCount] = useState(0)
  const [error, setError] = useState(null)

  const currentQuestion = questions.find(q => q.id === currentQuestionId)

  const handleSubmitAnswer = async () => {
    if (!answer.trim()) {
      setError('답변을 입력해주세요.')
      return
    }

    setIsLoading(true)
    setResponse('')
    setScore(null)
    setIsDone(false)
    setError(null)

    // SSE 스트리밍 처리 (Fetch + ReadableStream — 현대적 표준)
    try {
      const res = await fetch(`${apiBaseUrl}/interview/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          question_id: currentQuestionId,
          answer: answer,
        }),
      })

      if (!res.ok) {
        throw new Error(`서버 오류: ${res.status}`)
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        // 새로 수신한 청크만 디코딩해서 버퍼에 추가
        buffer += decoder.decode(value, { stream: true })

        // 완성된 SSE 이벤트 단위로 분리 (\n\n 기준)
        const events = buffer.split('\n\n')
        buffer = events.pop() // 마지막 미완성 청크는 버퍼에 보관

        for (const event of events) {
          if (!event.startsWith('data: ')) continue
          try {
            const data = JSON.parse(event.slice(6))
            if (data.text) {
              setResponse(prev => prev + data.text)
            }
            if (data.done) {
              setScore(data.score || 5)
              setIsDone(true)
            }
            if (data.error) {
              setError('오류: ' + data.error)
            }
          } catch (e) {
            // JSON 파싱 실패는 무시
          }
        }
      }
    } catch (err) {
      setError('답변 제출 실패: ' + (err.message || '알 수 없는 오류'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleNextQuestion = () => {
    if (currentQuestionId < questions.length) {
      setCurrentQuestionId(currentQuestionId + 1)
      setAnswer('')
      setResponse('')
      setScore(null)
      setIsDone(false)
      setError(null)
      setAnsweredCount(answeredCount + 1)
    } else {
      // 모든 질문 완료
      onComplete()
    }
  }

  const handleSkipQuestion = () => {
    if (currentQuestionId < questions.length) {
      setCurrentQuestionId(currentQuestionId + 1)
      setAnswer('')
      setResponse('')
      setScore(null)
      setIsDone(false)
      setError(null)
    } else {
      onComplete()
    }
  }

  return (
    <div className="container">
      <header>
        <div className="header-content">
          <h1>면접 진행 중</h1>
          <p className="subtitle">{persona.name}</p>
        </div>
      </header>

      <div className="content">
        {/* 진행 상황 */}
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${((answeredCount + 1) / questions.length) * 100}%` }}
          ></div>
        </div>
        <p className="progress-text">
          질문 {answeredCount + 1} / {questions.length}
        </p>

        <div className="card">
          {/* 질문 */}
          <div className="question-section">
            <div className="question-number">Q{currentQuestionId}</div>
            <h2 className="question-text">{currentQuestion?.question}</h2>
            <p className="question-meta">
              난이도: <span className={`difficulty ${currentQuestion?.difficulty}`}>
                {currentQuestion?.difficulty === 'easy' && '초급'}
                {currentQuestion?.difficulty === 'medium' && '중급'}
                {currentQuestion?.difficulty === 'hard' && '고급'}
              </span>
            </p>
          </div>

          {/* 답변 입력 */}
          {!isDone && (
            <div className="answer-input-section">
              <label htmlFor="answer">당신의 답변</label>
              <textarea
                id="answer"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="여기에 답변을 입력하세요..."
                disabled={isLoading}
              />
              <div className="button-group">
                <button
                  className="btn-primary"
                  onClick={handleSubmitAnswer}
                  disabled={isLoading || !answer.trim()}
                >
                  {isLoading ? (
                    <>
                      평가 중
                      <span className="loading" style={{ marginLeft: '6px', display: 'inline-block' }}></span>
                    </>
                  ) : (
                    '답변 제출'
                  )}
                </button>
                <button
                  className="btn-secondary"
                  onClick={handleSkipQuestion}
                  disabled={isLoading}
                >
                  건너뛰기
                </button>
              </div>
            </div>
          )}

          {/* AI 평가 응답 */}
          {response && (
            <div className="response-section">
              <div className="response-header">
                <h3>{persona.name}의 평가</h3>
                {score && <span className={`score score-${score}`}>{score}/10</span>}
              </div>
              <div className="response-content">
                {response}
              </div>
            </div>
          )}

          {/* 다음 질문 버튼 */}
          {isDone && (
            <div style={{ marginTop: '20px', textAlign: 'center' }}>
              <button className="btn-primary" onClick={handleNextQuestion}>
                {currentQuestionId < questions.length ? '다음 질문' : '결과 보기'}
              </button>
            </div>
          )}

          {error && (
            <div className="alert alert-error" style={{ marginTop: '16px' }}>
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default InterviewUI
