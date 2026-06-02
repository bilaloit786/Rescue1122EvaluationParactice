import { useNavigate } from 'react-router-dom'
import { useQuery } from 'react-query'
import api from '../../lib/api'
import { format } from 'date-fns'

export default function HistoryPage() {
  const navigate = useNavigate()
  const { data: history = [], isLoading } = useQuery('my-history', async () => {
    const { data } = await api.get('/api/test/history')
    return data
  })

  if (isLoading) return <div className="page-content"><div className="spinner" style={{ margin: '4rem auto' }} /></div>

  return (
    <div className="page-content fade-in">
      <div className="mobile-stack" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', gap: '0.75rem' }}>
        <h2>My Examination History</h2>
        <button className="btn btn-primary btn-sm" onClick={() => navigate('/staff/topics')}>+ New Test</button>
      </div>

      {history.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <div style={{ fontSize: 40, marginBottom: '0.75rem' }}>📝</div>
          <h3 style={{ marginBottom: 8 }}>No examinations yet</h3>
          <p style={{ color: 'var(--gray-300)', marginBottom: '1.25rem' }}>Take your first test to see results here.</p>
          <button className="btn btn-primary" onClick={() => navigate('/staff/topics')}>Start Examination</button>
        </div>
      ) : (
        <div className="card">
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Topic</th>
                  <th>Score</th>
                  <th>Result</th>
                  <th>Date</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {history.map(h => (
                  <tr key={h.id}>
                    <td style={{ fontWeight: 500 }}>{h.topic_label}</td>
                    <td>
                      <span style={{ fontSize: '1rem', fontWeight: 700, color: h.passed ? 'var(--green-700)' : 'var(--red-700)' }}>
                        {h.score_percent.toFixed(0)}%
                      </span>
                    </td>
                    <td><span className={`badge ${h.passed ? 'badge-pass' : 'badge-fail'}`}>{h.passed ? 'Passed' : 'Failed'}</span></td>
                    <td style={{ color: 'var(--gray-300)', fontSize: '0.82rem' }}>{format(new Date(h.completed_at), 'dd MMM yyyy, HH:mm')}</td>
                    <td>
                      <button className="btn btn-ghost btn-sm" onClick={() => navigate(`/staff/result?id=${h.id}`)}>View →</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
