import './LangToggle.css'

function LangToggle({ lang, onChange }) {
  return (
    <div className="lang-toggle-bar">
      <div className="lang-toggle">
        <button
          className={`lang-btn ${lang === 'ja' ? 'active' : ''}`}
          onClick={() => onChange('ja')}
        >
          日本語
        </button>
        <button
          className={`lang-btn ${lang === 'ko' ? 'active' : ''}`}
          onClick={() => onChange('ko')}
        >
          한국어
        </button>
      </div>
    </div>
  )
}

export default LangToggle
