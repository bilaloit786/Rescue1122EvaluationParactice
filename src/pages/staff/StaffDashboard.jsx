import { useNavigate } from 'react-router-dom'
import { useQuery } from 'react-query'
import { useAuth } from '../../context/AuthContext'
import api from '../../lib/api'
import { getDesignationLabel } from '../../lib/topics'
import { format } from 'date-fns'
import { BookOpen, TrendingUp, Award, ChevronRight } from 'lucide-react'

export default function StaffDashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const profile = user?.profile
  const designationLabel = getDesignationLabel(profile?.designation)

  const { data: history = [] } = useQuery('my-history', async () => {
    const { data } = await api.get('/api/test/history')
    return data
  })

  const passed  = history.filter(h => h.passed).length
  const avgScore = history.length ? (history.reduce((s, h) => s + h.score_percent, 0) / history.length).toFixed(1) : 0

  return (
    <div className="page-content fade-in">
      {/* Welcome */}
      <div className="card" style={{ background: 'linear-gradient(135deg, #042C53, #185FA5)', border: 'none', marginBottom: '1.5rem', padding: '1.75rem 2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1 style={{ color: '#fff', fontSize: '1.5rem', marginBottom: 4 }}>
              Welcome, {profile?.full_name?.split(' ')[0] || 'Officer'} 👋
            </h1>
            <p style={{ color: 'rgba(255,255,255,0.7)', margin: 0 }}>
              {designationLabel} · {profile?.district} District · Rescue 1122
            </p>
          </div>
          <button className="btn" style={{ background: 'rgba(255,255,255,0.15)', color: '#fff', border: '1px solid rgba(255,255,255,0.3)' }} onClick={() => navigate('/staff/topics')}>
            <BookOpen size={16} /> Start Examination
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid-3" style={{ marginBottom: '1.5rem' }}>
        {[
          { label: 'Tests Taken', value: history.length, icon: <BookOpen size={20} />, color: 'var(--blue-700)' },
          { label: 'Tests Passed', value: passed, icon: <Award size={20} />, color: 'var(--green-700)' },
          { label: 'Average Score', value: `${avgScore}%`, icon: <TrendingUp size={20} />, color: 'var(--amber-700)' },
        ].map(s => (
          <div key={s.label} className="stat-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div className="stat-label">{s.label}</div>
                <div className="stat-value" style={{ color: s.color }}>{s.value}</div>
              </div>
              <div style={{ color: s.color, opacity: 0.4 }}>{s.icon}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick action */}
      <div className="card card-hover" style={{ marginBottom: '1.5rem', cursor: 'pointer', border: '2px dashed var(--blue-200)' }} onClick={() => navigate('/staff/topics')}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: 48, height: 48, borderRadius: 12, background: 'var(--blue-50)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--blue-700)' }}>
            <BookOpen size={22} />
          </div>
          <div style={{ flex: 1 }}>
            <h3 style={{ color: 'var(--blue-800)', marginBottom: 2 }}>Take an Examination</h3>
            <p style={{ color: 'var(--gray-500)', fontSize: '0.875rem', margin: 0 }}>
              25 MCQs from the official document question bank. Receive instant answer review and feedback.
            </p>
          </div>
          <ChevronRight size={20} color="var(--blue-500)" />
        </div>
      </div>

      {/* Recent attempts */}
      {history.length > 0 && (
        <div className="card">
          <h3 style={{ marginBottom: '1rem' }}>Recent Results</h3>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Topic</th>
                  <th>Score</th>
                  <th>Result</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 8).map(h => (
                  <tr key={h.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/staff/result?id=${h.id}`)}>
                    <td style={{ fontWeight: 500 }}>{h.topic_label}</td>
                    <td><strong style={{ color: h.passed ? 'var(--green-700)' : 'var(--red-700)' }}>{h.score_percent.toFixed(0)}%</strong></td>
                    <td><span className={`badge ${h.passed ? 'badge-pass' : 'badge-fail'}`}>{h.passed ? 'Passed' : 'Failed'}</span></td>
                    <td style={{ color: 'var(--gray-300)', fontSize: '0.8rem' }}>{format(new Date(h.completed_at), 'dd MMM yyyy')}</td>
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
