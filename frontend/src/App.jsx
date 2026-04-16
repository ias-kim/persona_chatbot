import { useState, useEffect } from 'react'
import axios from 'axios'
import PersonaSelector from './components/PersonaSelector'
import InterviewUI from './components/InterviewUI'
import Results from './components/Results'
import LangToggle from './components/LangToggle'
import './App.css'

const API_BASE_URL = 'http://localhost:8000/api'

function App() {
  const [stage, setStage] = useState('persona-select') // persona-select, interview, results
  const [lang, setLang] = useState('ko')               // 'ko' | 'ja'
  const [selectedPersona, setSelectedPersona] = useState(null)
  const [personas, setPersonas] = useState([])
  const [questions, setQuestions] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // 초기 페르소나 로드
  useEffect(() => {
    const loadPersonas = async () => {
      try {
        setLoading(true)
        const res = await axios.get(`${API_BASE_URL}/personas`)
        setPersonas(res.data.personas)
      } catch (err) {
        setError('데이터 로드 실패: ' + (err.message || '알 수 없는 오류'))
      } finally {
        setLoading(false)
      }
    }
    loadPersonas()
  }, [])

  // 언어가 변경될 때마다 질문 다시 로드
  useEffect(() => {
    const loadQuestions = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/questions?lang=${lang}`)
        setQuestions(res.data.questions)
      } catch (err) {
        console.error('질문 로드 실패:', err)
      }
    }
    loadQuestions()
  }, [lang])

  // 언어 전환
  const handleLangChange = (newLang) => {
    setLang(newLang)
  }

  // 페르소나 선택 → 면접 시작 (페르소나별 질문 리스트 포함)
  const handleSelectPersona = async (persona) => {
    try {
      setLoading(true)
      const res = await axios.post(`${API_BASE_URL}/interview/start`, {
        persona: persona.id,
        lang,
      })
      setSelectedPersona(persona)
      setSessionId(res.data.session_id)
      setQuestions(res.data.questions)  // 페르소나별 질문으로 교체
      setStage('interview')
    } catch (err) {
      setError('면접 시작 실패: ' + (err.message || '알 수 없는 오류'))
    } finally {
      setLoading(false)
    }
  }

  // 면접 완료 → 결과 조회
  const handleInterviewComplete = async () => {
    try {
      const res = await axios.get(`${API_BASE_URL}/interview/results/${sessionId}`)
      setResults(res.data)
      setStage('results')
    } catch (err) {
      setError('결과 조회 실패: ' + (err.message || '알 수 없는 오류'))
    }
  }

  // 다시 시작
  const handleRestart = async () => {
    try {
      if (sessionId) {
        await axios.post(`${API_BASE_URL}/interview/reset`, { session_id: sessionId })
      }
      setStage('persona-select')
      setSelectedPersona(null)
      setSessionId(null)
      setResults(null)
      setError(null)
    } catch (err) {
      setError('초기화 실패: ' + (err.message || '알 수 없는 오류'))
    }
  }

  if (loading && stage === 'persona-select') {
    return (
      <div className="container">
        <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
          <p>로드 중...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      {/* 전역 언어 전환 버튼 — 항상 상단에 표시 */}
      <LangToggle lang={lang} onChange={handleLangChange} />

      {error && (
        <div className="container">
          <div className="alert alert-error">{error}</div>
        </div>
      )}

      {stage === 'persona-select' && (
        <PersonaSelector personas={personas} lang={lang} onSelect={handleSelectPersona} />
      )}

      {stage === 'interview' && selectedPersona && (
        <InterviewUI
          persona={selectedPersona}
          questions={questions}
          sessionId={sessionId}
          lang={lang}
          apiBaseUrl={API_BASE_URL}
          onComplete={handleInterviewComplete}
        />
      )}

      {stage === 'results' && results && (
        <Results
          results={results}
          questions={questions}
          lang={lang}
          onRestart={handleRestart}
        />
      )}
    </div>
  )
}

export default App
