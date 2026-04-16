import './PersonaSelector.css'

function PersonaSelector({ personas, onSelect }) {
  return (
    <div className="container">
      <header>
        <div className="header-content">
          <h1>페르소나 면접 챗봇</h1>
          <p className="subtitle">다양한 관점에서 면접 준비를 도와드립니다</p>
        </div>
      </header>

      <div className="content">
        <div className="card">
          <div className="card-header">페르소나 선택</div>
          <p style={{ marginBottom: '24px', color: '#666' }}>
            진행할 면접의 페르소나를 선택해주세요. 각 페르소나는 다른 관점에서 면접자를 평가합니다.
          </p>

          <div className="persona-grid">
            {personas.map((persona) => (
              <div
                key={persona.id}
                className="persona-card"
                onClick={() => onSelect(persona)}
              >
                <div className="persona-icon">
                  {persona.id === 'hr' && '👤'}
                  {persona.id === 'technical' && '💻'}
                  {persona.id === 'executive' && '👔'}
                </div>
                <h3>{persona.name}</h3>
                <p>{persona.description}</p>
                <button className="btn-primary" style={{ marginTop: '12px' }}>
                  선택
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="card" style={{ backgroundColor: '#eff6ff', borderLeft: '4px solid #3b82f6' }}>
          <div style={{ display: 'flex', gap: '12px' }}>
            <span style={{ fontSize: '20px' }}>💡</span>
            <div>
              <strong>팁</strong>
              <p style={{ marginTop: '4px', fontSize: '14px', color: '#1e40af' }}>
                각 페르소나와의 면접 후 결과를 비교해보세요. 다양한 각도에서 피드백을 받으면 더욱 효과적인 면접 준비가 가능합니다.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PersonaSelector
