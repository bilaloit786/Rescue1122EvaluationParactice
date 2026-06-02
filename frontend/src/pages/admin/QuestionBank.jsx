import { useMemo, useState } from 'react'
import { useQuery } from 'react-query'
import api from '../../lib/api'
import { Database, Filter, Search, X, Eye, HelpCircle } from 'lucide-react'

const letters = ['A', 'B', 'C', 'D']

function difficultyBadge(difficulty) {
  if (difficulty === 'easy') return 'badge-pass'
  if (difficulty === 'medium') return 'badge-blue'
  if (difficulty === 'hard') return 'badge-amber'
  return 'badge-gray'
}

function QuestionDetailsModal({ item, onClose }) {
  const answer = Number.isInteger(item.answer_index) ? item.answer_index : Number(item.answer_index)

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="detail-modal fade-in" onClick={e => e.stopPropagation()}>
        <div className="detail-hero">
          <button className="btn btn-icon btn-secondary detail-close" onClick={onClose} title="Close"><X size={16} /></button>
          <div className="avatar-mark"><HelpCircle size={26} /></div>
          <div style={{ minWidth: 0 }}>
            <h3>Question #{item.id}</h3>
            <p>{item.topic}</p>
            <div className="detail-pills">
              <span className={`badge ${difficultyBadge(item.difficulty)}`}>{item.difficulty}</span>
              <span className="badge badge-blue">{item.times_served} served</span>
              <span className="badge badge-amber">{item.times_wrong} wrong</span>
            </div>
          </div>
        </div>

        <div className="detail-section">
          <h4>Question</h4>
          <div className="feedback-box" style={{ fontWeight: 700, color: 'var(--gray-900)' }}>{item.question}</div>
        </div>

        <div className="detail-section">
          <h4>Options</h4>
          <div className="attempt-list">
            {(item.options || []).map((option, index) => (
              <div className={`attempt-card ${index === answer ? 'review-correct' : ''}`} key={`${item.id}-${index}`}>
                <div className="attempt-main">
                  <span className="mini-avatar">{letters[index] || index + 1}</span>
                  <div>
                    <strong>{option}</strong>
                    <span>{index === answer ? 'Correct answer' : 'Option'}</span>
                  </div>
                </div>
                {index === answer && <span className="badge badge-pass">Correct</span>}
              </div>
            ))}
          </div>
        </div>

        {item.explanation && (
          <div className="detail-section">
            <h4>Explanation</h4>
            <div className="feedback-box">{item.explanation}</div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function QuestionBank() {
  const [topic, setTopic] = useState('')
  const [difficulty, setDifficulty] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const [selected, setSelected] = useState(null)
  const limit = 10

  const params = useMemo(() => {
    const p = new URLSearchParams({ limit: String(limit), offset: String(page * limit) })
    if (topic) p.set('topic_id', topic)
    if (difficulty) p.set('difficulty', difficulty)
    if (search.trim()) p.set('search', search.trim())
    return p
  }, [difficulty, page, search, topic])

  const { data, isLoading } = useQuery(
    ['question-bank', topic, difficulty, search, page],
    async () => {
      const { data } = await api.get(`/api/admin/question-bank?${params}`)
      return data
    },
    { keepPreviousData: true }
  )

  const items = data?.items || []
  const topics = data?.topics || []
  const total = data?.total || 0
  const start = total ? page * limit + 1 : 0
  const end = Math.min((page + 1) * limit, total)

  const clearFilters = () => {
    setTopic('')
    setDifficulty('')
    setSearch('')
    setPage(0)
  }

  return (
    <div className="fade-in">
      <div className="mobile-stack" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', gap: '0.75rem' }}>
        <div>
          <h2><Database size={22} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 8, color: 'var(--blue-700)' }} />Question Bank</h2>
          <p style={{ color: 'var(--gray-500)', fontSize: '0.85rem', marginTop: 2 }}>
            {total} MCQs found · click any row to view full question and answer.
          </p>
        </div>
        <span className="badge badge-blue">{start}-{end} of {total}</span>
      </div>

      <div className="grid-3" style={{ marginBottom: '1rem' }}>
        <div className="stat-card">
          <div className="stat-label">Total MCQs</div>
          <div className="stat-value" style={{ color: 'var(--blue-700)' }}>{total}</div>
          <div className="stat-sub">matching current filters</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Topics</div>
          <div className="stat-value" style={{ color: 'var(--green-700)' }}>{topics.length}</div>
          <div className="stat-sub">available chapters/topics</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Page Size</div>
          <div className="stat-value" style={{ color: 'var(--amber-700)' }}>{limit}</div>
          <div className="stat-sub">questions per page</div>
        </div>
      </div>

      <div className="card card-sm mobile-stack" style={{ marginBottom: '1rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <Filter size={15} color="var(--gray-500)" style={{ alignSelf: 'center' }} />
        <div className="form-group mobile-full" style={{ margin: 0, minWidth: 220 }}>
          <label className="form-label">Topic</label>
          <select className="form-select" value={topic} onChange={e => { setTopic(e.target.value); setPage(0) }}>
            <option value="">All Topics</option>
            {topics.map(t => <option key={t.topic_id} value={t.topic_id}>{t.topic} ({t.total})</option>)}
          </select>
        </div>
        <div className="form-group mobile-full" style={{ margin: 0, minWidth: 150 }}>
          <label className="form-label">Difficulty</label>
          <select className="form-select" value={difficulty} onChange={e => { setDifficulty(e.target.value); setPage(0) }}>
            <option value="">All</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>
        <div className="form-group mobile-full" style={{ margin: 0, minWidth: 240, flex: 1 }}>
          <label className="form-label">Search</label>
          <div style={{ position: 'relative' }}>
            <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--gray-300)' }} />
            <input className="form-input" style={{ paddingLeft: 36 }} placeholder="Search question text..." value={search} onChange={e => { setSearch(e.target.value); setPage(0) }} />
          </div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={clearFilters}>Clear</button>
      </div>

      <div className="card">
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}><div className="spinner" style={{ margin: '0 auto' }} /></div>
        ) : items.length === 0 ? (
          <div className="empty-detail">No question bank records found for these filters.</div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Topic</th>
                  <th>Difficulty</th>
                  <th>Question</th>
                  <th>Answer</th>
                  <th>Served</th>
                  <th>Wrong</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => {
                  const answerIndex = Number(item.answer_index)
                  return (
                    <tr className="interactive-row" key={item.id} onClick={() => setSelected(item)} title="Click to view question details">
                      <td style={{ fontWeight: 700, color: 'var(--blue-700)' }}>#{item.id}</td>
                      <td style={{ fontWeight: 600, minWidth: 220 }}>{item.topic}</td>
                      <td><span className={`badge ${difficultyBadge(item.difficulty)}`}>{item.difficulty}</span></td>
                      <td style={{ maxWidth: 360, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.question}</td>
                      <td style={{ maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        <strong>{letters[answerIndex] || '-'}</strong> {item.options?.[answerIndex] || ''}
                      </td>
                      <td>{item.times_served}</td>
                      <td>{item.times_wrong}</td>
                      <td>
                        <button className="btn btn-icon btn-secondary" title="View question" onClick={(e) => { e.stopPropagation(); setSelected(item) }}>
                          <Eye size={14} />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="responsive-actions" style={{ justifyContent: 'space-between', marginTop: '1rem' }}>
        <button className="btn btn-secondary" disabled={page === 0} onClick={() => setPage(p => Math.max(0, p - 1))}>Previous</button>
        <span className="badge badge-gray">Page {page + 1}</span>
        <button className="btn btn-primary" disabled={end >= total} onClick={() => setPage(p => p + 1)}>Next</button>
      </div>

      {selected && <QuestionDetailsModal item={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
