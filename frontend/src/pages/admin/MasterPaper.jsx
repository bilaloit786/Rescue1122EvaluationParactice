import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from 'react-query'
import { CheckCircle, Eye, FileText, Printer, Sparkles, Trash2 } from 'lucide-react'
import api from '../../lib/api'

const letters = ['A', 'B', 'C', 'D']

function difficultyBadge(difficulty) {
  if (difficulty === 'easy') return 'badge-pass'
  if (difficulty === 'medium') return 'badge-blue'
  if (difficulty === 'hard') return 'badge-amber'
  return 'badge-gray'
}

function fieldBadge(field) {
  if (field === 'fire') return 'badge-fail'
  if (field === 'rescue') return 'badge-blue'
  if (field === 'building') return 'badge-pass'
  return 'badge-gray'
}

function formatDate(value) {
  if (!value) return ''
  return new Date(value).toLocaleString()
}

function questionText(question) {
  return question?.question || question?.q || ''
}

function questionOptions(question) {
  return question?.options || question?.opts || []
}

function MasterPaperPreview({ paper }) {
  if (!paper) {
    return (
      <div className="card" style={{ minHeight: 260, display: 'grid', placeItems: 'center', textAlign: 'center' }}>
        <div>
          <FileText size={38} color="var(--gray-300)" />
          <h3 style={{ marginTop: 10 }}>No Paper Selected</h3>
          <p style={{ color: 'var(--gray-500)', maxWidth: 420 }}>
            Generate a master paper or open a saved paper to review its questions and answer key.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="mobile-stack" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.75rem', marginBottom: '1rem' }}>
        <div>
          <h3 style={{ marginBottom: 4 }}>{paper.title}</h3>
          <p style={{ color: 'var(--gray-500)', fontSize: '0.85rem' }}>
            {paper.total_questions} questions · {paper.easy_count} easy · {paper.medium_count} medium · {paper.hard_count} hard
          </p>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={() => window.print()}>
          <Printer size={15} /> Print
        </button>
      </div>

      <div className="attempt-list">
        {(paper.questions || []).map((question, index) => {
          const answer = Number(question.answer_index ?? question.ans)
          const options = questionOptions(question)
          return (
            <div className="review-card" key={`${question.bank_question_id || question.id}-${index}`}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', alignItems: 'flex-start', marginBottom: 10 }}>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <span className="badge badge-gray">Q{index + 1}</span>
                  <span className={`badge ${fieldBadge(question.field)}`}>{question.field}</span>
                  <span className={`badge ${difficultyBadge(question.difficulty)}`}>{question.difficulty}</span>
                </div>
                <span className="badge badge-blue">{question.topic}</span>
              </div>

              <strong style={{ display: 'block', color: 'var(--gray-900)', lineHeight: 1.45, marginBottom: 12 }}>
                {questionText(question)}
              </strong>

              <div className="attempt-list">
                {options.map((option, optionIndex) => (
                  <div className={`attempt-card ${optionIndex === answer ? 'review-correct' : ''}`} key={`${question.id}-${optionIndex}`}>
                    <div className="attempt-main">
                      <span className="mini-avatar">{letters[optionIndex] || optionIndex + 1}</span>
                      <div>
                        <strong>{option}</strong>
                        <span>{optionIndex === answer ? 'Correct answer' : 'Option'}</span>
                      </div>
                    </div>
                    {optionIndex === answer && <CheckCircle size={16} color="var(--green-700)" />}
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function MasterPaper() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({
    title: 'Competent Authority Master Test',
    easy_count: 10,
    medium_count: 8,
    hard_count: 7,
  })
  const [selectedPaper, setSelectedPaper] = useState(null)
  const [error, setError] = useState('')

  const { data: papers = [], isLoading } = useQuery('master-papers', async () => {
    const { data } = await api.get('/api/admin/master-papers')
    return data
  })

  const generateMutation = useMutation(
    async () => {
      const payload = {
        title: form.title.trim(),
        easy_count: Number(form.easy_count),
        medium_count: Number(form.medium_count),
        hard_count: Number(form.hard_count),
      }
      const { data } = await api.post('/api/admin/master-papers', payload)
      return data
    },
    {
      onSuccess: paper => {
        setError('')
        setSelectedPaper(paper)
        queryClient.invalidateQueries('master-papers')
      },
      onError: err => setError(err.response?.data?.detail || 'Unable to generate paper.'),
    }
  )

  const loadPaperMutation = useMutation(
    async paperId => {
      const { data } = await api.get(`/api/admin/master-papers/${paperId}`)
      return data
    },
    {
      onSuccess: paper => {
        setError('')
        setSelectedPaper(paper)
      },
      onError: err => setError(err.response?.data?.detail || 'Unable to open paper.'),
    }
  )

  const deleteMutation = useMutation(
    async paperId => {
      await api.delete(`/api/admin/master-papers/${paperId}`)
      return paperId
    },
    {
      onSuccess: paperId => {
        setError('')
        if (selectedPaper?.id === paperId) setSelectedPaper(null)
        queryClient.invalidateQueries('master-papers')
      },
      onError: err => setError(err.response?.data?.detail || 'Unable to delete paper.'),
    }
  )

  const total = Number(form.easy_count || 0) + Number(form.medium_count || 0) + Number(form.hard_count || 0)
  const canGenerate = form.title.trim().length >= 3 && total === 25 && !generateMutation.isLoading

  const handleCountChange = (key, value) => {
    setForm(current => ({ ...current, [key]: value }))
  }

  return (
    <div className="fade-in">
      <div className="mobile-stack" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', gap: '0.75rem' }}>
        <div>
          <h2><FileText size={22} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 8, color: 'var(--blue-700)' }} />Master Paper</h2>
          <p style={{ color: 'var(--gray-500)', fontSize: '0.85rem', marginTop: 2 }}>
            Generate an official 25 question paper from Fire, Rescue, and Building MCQs.
          </p>
        </div>
        <span className="badge badge-blue">{papers.length} saved</span>
      </div>

      <div className="grid-3" style={{ marginBottom: '1rem' }}>
        <div className="stat-card">
          <div className="stat-label">Easy</div>
          <div className="stat-value" style={{ color: 'var(--green-700)' }}>{form.easy_count}</div>
          <div className="stat-sub">default paper count</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Medium</div>
          <div className="stat-value" style={{ color: 'var(--blue-700)' }}>{form.medium_count}</div>
          <div className="stat-sub">default paper count</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Hard</div>
          <div className="stat-value" style={{ color: 'var(--amber-700)' }}>{form.hard_count}</div>
          <div className="stat-sub">default paper count</div>
        </div>
      </div>

      <div className="card card-sm" style={{ marginBottom: '1rem' }}>
        <form
          className="responsive-form-grid"
          onSubmit={event => {
            event.preventDefault()
            if (canGenerate) generateMutation.mutate()
          }}
        >
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Paper Name</label>
            <input
              className="form-input"
              value={form.title}
              onChange={event => setForm(current => ({ ...current, title: event.target.value }))}
              placeholder="Competent Authority Master Test"
              maxLength={120}
            />
          </div>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Question Mix</label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
              <input className="form-input" type="number" min="3" max="25" value={form.easy_count} onChange={event => handleCountChange('easy_count', event.target.value)} title="Easy questions" />
              <input className="form-input" type="number" min="0" max="25" value={form.medium_count} onChange={event => handleCountChange('medium_count', event.target.value)} title="Medium questions" />
              <input className="form-input" type="number" min="0" max="25" value={form.hard_count} onChange={event => handleCountChange('hard_count', event.target.value)} title="Hard questions" />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginTop: 6 }}>
              <span style={{ color: 'var(--gray-500)', fontSize: '0.75rem' }}>Easy · Medium · Hard</span>
              <span className={`badge ${total === 25 ? 'badge-pass' : 'badge-fail'}`}>Total {total}/25</span>
            </div>
          </div>
          <div className="responsive-actions" style={{ alignItems: 'flex-end', justifyContent: 'flex-end' }}>
            <button className="btn btn-primary" type="submit" disabled={!canGenerate}>
              {generateMutation.isLoading ? <span className="spinner" /> : <Sparkles size={16} />}
              Generate Paper
            </button>
          </div>
        </form>
        {error && <div className="feedback-box" style={{ marginTop: 12, color: 'var(--red-700)' }}>{error}</div>}
      </div>

      <div className="grid-2" style={{ alignItems: 'start' }}>
        <div className="card">
          <h3 style={{ marginBottom: '1rem' }}>Saved Papers</h3>
          {isLoading ? (
            <div style={{ textAlign: 'center', padding: '2rem' }}><div className="spinner" style={{ margin: '0 auto' }} /></div>
          ) : papers.length === 0 ? (
            <div className="empty-detail">No master papers generated yet.</div>
          ) : (
            <div className="attempt-list">
              {papers.map(paper => (
                <div className="attempt-card" key={paper.id}>
                  <div className="attempt-main">
                    <span className="mini-avatar"><FileText size={15} /></span>
                    <div>
                      <strong>{paper.title}</strong>
                      <span>{paper.total_questions} questions · {formatDate(paper.created_at)}</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn-icon btn-secondary" title="View paper" onClick={() => loadPaperMutation.mutate(paper.id)}>
                      <Eye size={15} />
                    </button>
                    <button className="btn btn-icon btn-secondary" title="Delete paper" style={{ color: 'var(--red-700)' }} onClick={() => deleteMutation.mutate(paper.id)}>
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <MasterPaperPreview paper={selectedPaper} />
      </div>
    </div>
  )
}
