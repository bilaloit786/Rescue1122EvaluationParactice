import { useState, useEffect, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import api from '../../lib/api'
import toast from 'react-hot-toast'
import { AlertTriangle, ChevronLeft, ChevronRight, Clock, Send } from 'lucide-react'

const TEST_DURATION_SECONDS = 30 * 60

export default function ExamPage() {
  const { state } = useLocation()
  const navigate = useNavigate()
  const topic = state?.topic
  const designation = state?.designation

  const [questions, setQuestions]   = useState([])
  const [answers, setAnswers]       = useState({})   // { q_index: selected }
  const [current, setCurrent]       = useState(0)
  const [loading, setLoading]       = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError]           = useState(null)
  const [timeLeft, setTimeLeft]     = useState(TEST_DURATION_SECONDS)
  const [showSubmitWarning, setShowSubmitWarning] = useState(false)
  const startedAt    = useRef(new Date().toISOString())
  const startedAtMs  = useRef(Date.now())
  const timerRef     = useRef(null)
  const timerStarted = useRef(false)
  const submittingRef = useRef(false)
  const questionsRef = useRef([])
  const answersRef   = useRef({})

  useEffect(() => { questionsRef.current = questions }, [questions])
  useEffect(() => { answersRef.current = answers }, [answers])

  useEffect(() => {
    if (!topic) { navigate('/staff/topics'); return }
    loadQuestions()
    return () => clearInterval(timerRef.current)
  }, [])

  useEffect(() => {
    if (loading || error || !questions.length || timerStarted.current) return
    timerStarted.current = true
    startedAt.current = new Date().toISOString()
    startedAtMs.current = Date.now()
    timerRef.current = setInterval(() => {
      setTimeLeft(seconds => {
        if (seconds <= 1) {
          clearInterval(timerRef.current)
          setTimeout(() => submitTest({ auto: true }), 0)
          return 0
        }
        return seconds - 1
      })
    }, 1000)
  }, [loading, error, questions.length])

  const loadQuestions = async () => {
    setLoading(true); setError(null)
    try {
      const { data } = await api.post('/api/test/generate', { topic_id: topic.id, designation })
      setQuestions(data.questions)
    } catch (e) {
      setError('Failed to generate questions. Check your connection and try again.')
    } finally { setLoading(false) }
  }

  const formatTime = (s) => `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`

  const answered   = Object.keys(answers).length
  const progress   = questions.length ? Math.round((answered / questions.length) * 100) : 0
  const q          = questions[current]
  const unanswered = Math.max(questions.length - answered, 0)
  const timerTone  = timeLeft <= 300 ? 'danger' : timeLeft <= 600 ? 'warning' : 'normal'

  const handleSelect = (optIdx) => {
    setAnswers(a => ({ ...a, [current]: optIdx }))
  }

  const requestSubmit = () => {
    setShowSubmitWarning(true)
  }

  async function submitTest({ auto = false } = {}) {
    if (submittingRef.current) return
    submittingRef.current = true
    setSubmitting(true)
    setShowSubmitWarning(false)
    try {
      const latestQuestions = questionsRef.current
      const latestAnswers = answersRef.current
      const answerList = latestQuestions.map((_, i) => ({ q_index: i, selected: latestAnswers[i] ?? -1 }))
      const timeTaken = Math.min(TEST_DURATION_SECONDS, Math.max(0, Math.floor((Date.now() - startedAtMs.current) / 1000)))
      const { data } = await api.post('/api/test/submit', {
        topic_id: topic.id,
        topic_label: topic.label,
        questions: latestQuestions,
        answers: answerList,
        started_at: startedAt.current,
        time_taken_seconds: timeTaken,
      })
      clearInterval(timerRef.current)
      if (auto) toast.success('Time finished. Your examination was submitted automatically.')
      navigate('/staff/result', { state: { attempt: data }, replace: true })
    } catch (e) {
      toast.error('Submission failed. Please try again.')
      submittingRef.current = false
      setSubmitting(false)
    }
  }

  if (!topic) return null

  if (loading) return (
    <div className="page-content" style={{ textAlign: 'center', paddingTop: '4rem' }}>
      <div className="spinner" style={{ margin: '0 auto 1rem' }} />
      <h3 style={{ color: 'var(--blue-700)', marginBottom: 8 }}>Preparing your practice examination…</h3>
      <p style={{ color: 'var(--gray-300)' }}>Selecting 10 easy, 10 medium, and 5 hard MCQs from the question bank</p>
    </div>
  )

  if (error) return (
    <div className="page-content">
      <div className="alert alert-error" style={{ marginBottom: '1rem' }}>{error}</div>
      <div className="responsive-actions">
        <button className="btn btn-secondary" onClick={() => navigate('/staff/topics')}>← Back</button>
        <button className="btn btn-primary" onClick={loadQuestions}>Retry</button>
      </div>
    </div>
  )

  return (
    <div className="page-content fade-in">
      {/* Top bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <h3 style={{ marginBottom: 2 }}>{topic.icon} {topic.label}</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--gray-300)', margin: 0 }}>{answered} of {questions.length} answered</p>
        </div>
        <div className={`exam-timer exam-timer-${timerTone}`}>
          <Clock size={15} /> {formatTime(timeLeft)}
        </div>
      </div>

      {/* Progress */}
      <div className="progress-track" style={{ marginBottom: '1.5rem' }}>
        <div className="progress-bar" style={{ width: `${progress}%` }} />
      </div>

      {/* Question card */}
      {q && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--gray-300)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{q.topic || 'General'}</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--gray-300)' }}>Q {current + 1} / {questions.length}</span>
          </div>
          <p style={{ fontSize: '1rem', fontWeight: 500, color: 'var(--gray-900)', marginBottom: '1.25rem', lineHeight: 1.6 }}>{q.q}</p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {q.opts.map((opt, i) => {
              const isSelected = answers[current] === i
              const letters = ['A', 'B', 'C', 'D']
              return (
                <button key={i} className="exam-option" onClick={() => handleSelect(i)} style={{
                  display: 'flex', alignItems: 'flex-start', gap: '0.75rem', padding: '12px 16px',
                  border: isSelected ? '2px solid var(--blue-500)' : '1.5px solid var(--gray-100)',
                  borderRadius: 'var(--radius-md)', background: isSelected ? 'linear-gradient(135deg, var(--blue-50), var(--green-50))' : 'linear-gradient(180deg, #fff, var(--surface-blue))',
                  cursor: 'pointer', textAlign: 'left', width: '100%', transition: 'all 0.15s', fontFamily: 'var(--font-sans)',
                }}>
                  <span style={{ width: 26, height: 26, borderRadius: '50%', background: isSelected ? 'var(--blue-700)' : 'var(--gray-50)', color: isSelected ? '#fff' : 'var(--gray-500)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.78rem', fontWeight: 700, flexShrink: 0, border: isSelected ? 'none' : '1.5px solid var(--gray-100)' }}>
                    {letters[i]}
                  </span>
                  <span style={{ fontSize: '0.9rem', color: isSelected ? 'var(--blue-800)' : 'var(--gray-700)', fontWeight: isSelected ? 500 : 400, lineHeight: 1.5 }}>{opt}</span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Question navigator dots */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '1.25rem' }}>
        {questions.map((_, i) => (
          <button key={i} onClick={() => setCurrent(i)} style={{
            width: 32, height: 32, borderRadius: 6, border: i === current ? '2px solid var(--blue-700)' : '1.5px solid var(--gray-100)',
            background: answers[i] !== undefined ? 'var(--blue-700)' : i === current ? 'var(--blue-50)' : 'var(--gray-50)',
            color: answers[i] !== undefined ? '#fff' : i === current ? 'var(--blue-700)' : 'var(--gray-500)',
            fontSize: '0.72rem', fontWeight: 600, cursor: 'pointer', fontFamily: 'var(--font-sans)',
          }}>{i + 1}</button>
        ))}
      </div>

      {/* Navigation */}
      <div className="mobile-stack" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem' }}>
        <button className="btn btn-secondary" disabled={current === 0} onClick={() => setCurrent(c => c - 1)}>
          <ChevronLeft size={16} /> Previous
        </button>
        <div className="mobile-full" style={{ display: 'flex', gap: '0.75rem' }}>
          {current < questions.length - 1 ? (
            <button className="btn btn-primary" onClick={() => setCurrent(c => c + 1)}>
              Next <ChevronRight size={16} />
            </button>
          ) : (
            <button className="btn btn-primary" onClick={requestSubmit} disabled={submitting}>
              {submitting ? <><span className="spinner spinner-sm" /> Submitting…</> : <><Send size={15} /> Submit Examination</>}
            </button>
          )}
        </div>
      </div>

      {showSubmitWarning && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="submit-warning-title">
          <div className="detail-modal submit-warning-modal">
            <div className="detail-hero">
              <div className="avatar-mark"><AlertTriangle size={28} /></div>
              <div>
                <h3 id="submit-warning-title">Final Submission</h3>
                <p>{unanswered > 0 ? `You still have ${unanswered} unanswered question(s).` : 'All questions are answered.'}</p>
              </div>
            </div>
            <div className="detail-section">
              <h4>Are you sure you want to submit?</h4>
              <p style={{ marginBottom: '1rem' }}>
                After final submission, your answers will be checked and the result report will open. You cannot return to change this attempt.
              </p>
              <div className="responsive-actions">
                <button className="btn btn-secondary" onClick={() => setShowSubmitWarning(false)} disabled={submitting}>
                  Continue Test
                </button>
                <button className="btn btn-primary" onClick={() => submitTest()} disabled={submitting}>
                  {submitting ? <><span className="spinner spinner-sm" /> Submitting…</> : <><Send size={15} /> Final Submit</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
