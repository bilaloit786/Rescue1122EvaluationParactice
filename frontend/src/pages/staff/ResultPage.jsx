import { useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from 'react-query'
import api from '../../lib/api'
import { format } from 'date-fns'
import { CheckCircle, XCircle, RotateCcw, BookOpen, Mail, Lightbulb } from 'lucide-react'

function ScoreArc({ pct }) {
  const r = 52; const circ = 2 * Math.PI * r
  const offset = circ - (pct / 100) * circ
  const color = pct >= 75 ? '#639922' : pct >= 60 ? '#185FA5' : '#D85A30'
  return (
    <svg width="130" height="130" viewBox="0 0 130 130">
      <circle cx="65" cy="65" r={r} fill="none" stroke="#E8E8E8" strokeWidth="10" />
      <circle cx="65" cy="65" r={r} fill="none" stroke={color} strokeWidth="10"
        strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
        transform="rotate(-90 65 65)" style={{ transition: 'stroke-dashoffset 1s ease' }} />
      <text x="65" y="60" textAnchor="middle" fontSize="22" fontWeight="700" fill={color} fontFamily="DM Sans,sans-serif">{Math.round(pct)}%</text>
      <text x="65" y="78" textAnchor="middle" fontSize="11" fill="#888" fontFamily="DM Sans,sans-serif">{pct >= 60 ? 'PASSED' : 'FAILED'}</text>
    </svg>
  )
}

export default function ResultPage() {
  const { state } = useLocation()
  const navigate = useNavigate()
  const attemptFromNav = state?.attempt
  const params = new URLSearchParams(window.location.search)
  const attemptId = params.get('id')

  const { data: attemptFromApi } = useQuery(
    ['attempt', attemptId],
    () => api.get(`/api/test/attempt/${attemptId}`).then(r => r.data),
    { enabled: !attemptFromNav && !!attemptId }
  )

  const attempt = attemptFromNav || attemptFromApi
  if (!attempt) return <div className="page-content"><div className="spinner" style={{ margin: '4rem auto' }} /></div>

  const { score_percent, correct_answers, total_questions, passed, topic_label, ai_feedback, subtopic_scores, completed_at, email_sent } = attempt
  const subtopics = subtopic_scores ? Object.entries(subtopic_scores) : []
  const answerRows = (attempt.questions || []).map((q, i) => {
    const answer = (attempt.answers || []).find(a => a.q_index === i)
    const selected = answer?.selected ?? -1
    const correct = answer?.correct ?? q.ans
    return {
      question: q,
      selected,
      correct,
      isCorrect: selected === correct,
    }
  })

  return (
    <div className="page-content fade-in">
      <h2 style={{ marginBottom: '1.5rem' }}>Examination Result</h2>

      {/* Main result card */}
      <div className="card" style={{ marginBottom: '1rem', textAlign: 'center', padding: '2rem' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
          <ScoreArc pct={score_percent} />
          <span className={`badge ${passed ? 'badge-pass' : 'badge-fail'}`} style={{ fontSize: '0.85rem', padding: '5px 16px' }}>
            {passed ? <CheckCircle size={13} style={{ marginRight: 4 }} /> : <XCircle size={13} style={{ marginRight: 4 }} />}
            {passed ? 'PASSED' : 'FAILED — Retest Required'}
          </span>
          <h3 style={{ color: 'var(--gray-900)' }}>{topic_label}</h3>
          <p style={{ color: 'var(--gray-400)', fontSize: '0.8rem' }}>{correct_answers} correct out of {total_questions} · {completed_at ? format(new Date(completed_at), 'dd MMM yyyy, HH:mm') : ''}</p>
          {email_sent && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.78rem', color: 'var(--green-700)', background: 'var(--green-50)', padding: '4px 12px', borderRadius: 99 }}>
              <Mail size={12} /> Result emailed to you
            </div>
          )}
        </div>
      </div>

      {/* Stats row */}
      <div className="grid-3" style={{ marginBottom: '1rem' }}>
        {[
          { label: 'Correct', value: correct_answers, color: 'var(--green-700)' },
          { label: 'Incorrect', value: total_questions - correct_answers, color: 'var(--red-700)' },
          { label: 'Weak Areas', value: subtopics.filter(([, v]) => v.percent < 60).length, color: 'var(--amber-700)' },
        ].map(s => (
          <div key={s.label} className="stat-card" style={{ textAlign: 'center' }}>
            <div className="stat-label">{s.label}</div>
            <div className="stat-value" style={{ color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Sub-topic breakdown */}
      {subtopics.length > 0 && (
        <div className="card" style={{ marginBottom: '1rem' }}>
          <h4 style={{ marginBottom: '1rem' }}>Performance by Sub-topic</h4>
          {subtopics.map(([name, data]) => {
            const pct = data.percent || 0
            const color = pct >= 75 ? 'var(--green-500)' : pct >= 60 ? 'var(--blue-500)' : 'var(--red-500)'
            return (
              <div key={name} className="mobile-stack" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.6rem' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--gray-500)', minWidth: 160 }}>{name}</span>
                <div className="progress-track" style={{ flex: 1 }}>
                  <div className="progress-bar" style={{ width: `${pct}%`, background: color }} />
                </div>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color, minWidth: 38, textAlign: 'right' }}>{Math.round(pct)}%</span>
                <span style={{ fontSize: '0.72rem', color: 'var(--gray-300)', minWidth: 40 }}>{data.correct}/{data.total}</span>
              </div>
            )
          })}
        </div>
      )}

      {/* AI Feedback */}
      {ai_feedback && (
        <div className="card" style={{ marginBottom: '1.5rem', background: passed ? 'var(--green-50)' : 'var(--blue-50)', border: `1px solid ${passed ? 'var(--green-100)' : 'var(--blue-200)'}` }}>
          <h4 style={{ marginBottom: '0.75rem', color: passed ? 'var(--green-700)' : 'var(--blue-800)' }}>Evaluation & Recommendations</h4>
          {ai_feedback.split('\n').filter(l => l.trim()).map((para, i) => (
            <p key={i} style={{ fontSize: '0.9rem', color: 'var(--gray-700)', marginBottom: '0.6rem', lineHeight: 1.7 }}>{para}</p>
          ))}
        </div>
      )}

      {answerRows.length > 0 && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <h4 style={{ marginBottom: '1rem' }}>Answer Review</h4>
          <div style={{ display: 'grid', gap: '0.85rem' }}>
            {answerRows.map(({ question, selected, correct, isCorrect }, index) => (
              <div key={question.id || index} className={`review-card ${isCorrect ? 'review-correct' : 'review-wrong'}`}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'flex-start', marginBottom: '0.65rem' }}>
                  <div>
                    <span className="detail-label">Question {index + 1} · {question.topic || 'General'}</span>
                    <p style={{ color: 'var(--gray-900)', fontWeight: 600, marginTop: 4 }}>{question.q}</p>
                  </div>
                  <span className={`badge ${isCorrect ? 'badge-pass' : 'badge-fail'}`}>
                    {isCorrect ? <CheckCircle size={12} /> : <XCircle size={12} />}
                    {isCorrect ? 'Correct' : 'Review'}
                  </span>
                </div>
                <div className="review-answer-grid">
                  <div>
                    <div className="detail-label">Your Answer</div>
                    <div className="detail-value">{selected >= 0 ? question.opts?.[selected] : 'Unanswered'}</div>
                  </div>
                  <div>
                    <div className="detail-label">Correct Answer</div>
                    <div className="detail-value">{question.opts?.[correct] || '—'}</div>
                  </div>
                </div>
                {question.explanation && (
                  <div className="review-explanation">
                    <Lightbulb size={14} />
                    <span>{question.explanation}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="responsive-actions">
        <button className="btn btn-secondary" onClick={() => navigate('/staff/topics')}>
          <RotateCcw size={15} /> Retake / New Topic
        </button>
        <button className="btn btn-primary" onClick={() => navigate('/staff')}>
          <BookOpen size={15} /> Back to Dashboard
        </button>
      </div>
    </div>
  )
}
