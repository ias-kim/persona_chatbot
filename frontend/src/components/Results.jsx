import './Results.css'

function Results({ results, lang, onRestart }) {
  const accuracyPercent = Math.round(results.accuracy_rate * 100)

  return (
    <div className="container">
      <header>
        <div className="header-content">
          <h1>면접 결과</h1>
          <p className="subtitle">{results.persona}</p>
        </div>
      </header>

      <div className="content">
        {/* 통계 섹션 */}
        <div className="card">
          <div className="card-header">통계</div>

          <div className="stats">
            <div className="stat-item">
              <div className="stat-value">{results.total_questions}</div>
              <div className="stat-label">전체 질문</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{results.answered_count}</div>
              <div className="stat-label">답변한 질문</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{results.total_questions - results.answered_count}</div>
              <div className="stat-label">건너뛴 질문</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{accuracyPercent}%</div>
              <div className="stat-label">정답률</div>
            </div>
          </div>
        </div>

        {/* 상세 답변 섹션 */}
        <div className="card">
          <div className="card-header">상세 답변</div>

          <div className="answers-list">
            {results.answers.map((answer, idx) => (
              <div key={idx} className="answer-item">
                <div className="answer-header">
                  <h3>Q{answer.question_id}: {answer.question}</h3>
                  <span className={`score score-${answer.score}`}>
                    {answer.score}/10
                  </span>
                </div>

                <div className="feedback-section">
                  <p className="feedback-label">피드백:</p>
                  <div className="feedback-text">
                    {answer.feedback}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 액션 버튼 */}
        <div className="card" style={{ textAlign: 'center' }}>
          <button className="btn-primary" onClick={onRestart} style={{ marginRight: '12px' }}>
            다시 시작
          </button>
          <button className="btn-secondary" onClick={() => window.print()}>
            결과 인쇄
          </button>
        </div>
      </div>
    </div>
  )
}

export default Results
