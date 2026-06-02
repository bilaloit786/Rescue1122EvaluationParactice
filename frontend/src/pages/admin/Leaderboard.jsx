import { useState } from 'react'
import { useQuery } from 'react-query'
import api from '../../lib/api'
import { DISTRICTS, getDesignationLabel } from '../../lib/topics'
import { Trophy, Medal } from 'lucide-react'
import { StaffDetailsModal } from './StaffManagement'

const rankStyle = (rank) => {
  if (rank === 1) return { color: '#B8860B', fontWeight: 700 }
  if (rank === 2) return { color: '#71797E', fontWeight: 700 }
  if (rank === 3) return { color: '#CD7F32', fontWeight: 700 }
  return { color: 'var(--gray-300)' }
}

const rankIcon = (rank) => {
  if (rank === 1) return '🥇'
  if (rank === 2) return '🥈'
  if (rank === 3) return '🥉'
  return rank
}

export default function Leaderboard() {
  const [district, setDistrict] = useState('')
  const [topic, setTopic]       = useState('')
  const [selectedStaff, setSelectedStaff] = useState(null)

  const { data: board = [], isLoading } = useQuery(
    ['leaderboard', district, topic],
    async () => {
      const params = new URLSearchParams({ limit: '100' })
      if (district) params.set('district', district)
      if (topic)    params.set('topic', topic)
      const { data } = await api.get(`/api/admin/leaderboard?${params}`)
      return data
    }
  )

  const topThree = board.slice(0, 3)

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h2><Trophy size={22} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 8, color: 'var(--amber-700)' }} />District Leaderboard</h2>
          <p style={{ color: 'var(--gray-300)', fontSize: '0.85rem', marginTop: 2 }}>Ranked by average score across all examinations</p>
        </div>
      </div>

      {/* Filters */}
      <div className="card card-sm mobile-stack" style={{ marginBottom: '1.5rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div className="form-group mobile-full" style={{ margin: 0, minWidth: 160 }}>
          <label className="form-label">Filter by District</label>
          <select className="form-select" value={district} onChange={e => setDistrict(e.target.value)}>
            <option value="">All Districts</option>
            {DISTRICTS.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div className="form-group mobile-full" style={{ margin: 0, minWidth: 220 }}>
          <label className="form-label">Filter by Topic</label>
          <input className="form-input" placeholder="e.g. Fire Chemistry…" value={topic} onChange={e => setTopic(e.target.value)} />
        </div>
        <button className="btn btn-ghost btn-sm" onClick={() => { setDistrict(''); setTopic('') }}>Clear</button>
      </div>

      {/* Top 3 podium */}
      {!isLoading && topThree.length >= 3 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
          {[topThree[1], topThree[0], topThree[2]].map((s, idx) => {
            const actualRank = idx === 0 ? 2 : idx === 1 ? 1 : 3
            const heights = [130, 160, 110]
            const h = heights[idx]
            return (
              <div
                key={s.user_id || s.name}
                className="podium-card"
                style={{ textAlign: 'center', minWidth: 140 }}
                onClick={() => setSelectedStaff({
                  id: s.user_id,
                  username: s.username,
                  email: s.email,
                  is_active: true,
                  profile: { full_name: s.name, designation: s.designation, district: s.district },
                })}
                title="Click to view staff details"
              >
                <div style={{ fontSize: 32, marginBottom: 6 }}>{rankIcon(actualRank)}</div>
                <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: 2, color: 'var(--gray-900)' }}>{s.name}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--gray-300)', marginBottom: 8 }}>{s.district}</div>
                <div style={{ height: h, background: actualRank === 1 ? 'var(--blue-700)' : actualRank === 2 ? 'var(--gray-300)' : 'var(--amber-500)', borderRadius: '10px 10px 0 0', display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: 12 }}>
                  <span style={{ color: '#fff', fontWeight: 700, fontSize: '1.1rem' }}>{s.avg_score}%</span>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Full table */}
      <div className="card">
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}><div className="spinner" style={{ margin: '0 auto' }} /></div>
        ) : board.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--gray-300)' }}>
            <Medal size={40} style={{ marginBottom: 12, opacity: 0.3 }} />
            <p>No data yet. Results will appear here after staff take examinations.</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr><th style={{ width: 50 }}>Rank</th><th>Name</th><th>Designation</th><th>District</th><th>Avg Score</th><th>Tests Taken</th><th>Tests Passed</th><th>Pass Rate</th></tr>
              </thead>
              <tbody>
                {board.map(s => (
                  <tr
                    className="interactive-row"
                    key={s.user_id || s.rank}
                    style={{ background: s.rank <= 3 ? 'var(--amber-50)' : undefined }}
                    onClick={() => setSelectedStaff({
                      id: s.user_id,
                      username: s.username,
                      email: s.email,
                      is_active: true,
                      profile: { full_name: s.name, designation: s.designation, district: s.district },
                    })}
                    title="Click to view staff details"
                  >
                    <td style={{ textAlign: 'center', ...rankStyle(s.rank), fontSize: s.rank <= 3 ? '1.1rem' : '0.9rem' }}>{rankIcon(s.rank)}</td>
                    <td style={{ fontWeight: 500 }}>{s.name}</td>
                    <td><span className="badge badge-blue" style={{ fontSize: '0.7rem' }}>{getDesignationLabel(s.designation)}</span></td>
                    <td>{s.district}</td>
                    <td>
                      <strong style={{ fontSize: '1rem', color: s.avg_score >= 75 ? 'var(--green-700)' : s.avg_score >= 60 ? 'var(--blue-700)' : 'var(--red-700)' }}>
                        {s.avg_score}%
                      </strong>
                    </td>
                    <td style={{ textAlign: 'center' }}>{s.total_tests}</td>
                    <td style={{ textAlign: 'center' }}>{s.total_passed}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div className="progress-track" style={{ width: 80 }}>
                          <div className="progress-bar" style={{ width: `${s.total_tests ? (s.total_passed / s.total_tests * 100) : 0}%`, background: 'var(--green-500)' }} />
                        </div>
                        <span style={{ fontSize: '0.78rem', color: 'var(--gray-300)' }}>
                          {s.total_tests ? Math.round(s.total_passed / s.total_tests * 100) : 0}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {selectedStaff && (
        <StaffDetailsModal staff={selectedStaff} onClose={() => setSelectedStaff(null)} />
      )}
    </div>
  )
}
