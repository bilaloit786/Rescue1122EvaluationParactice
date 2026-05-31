import { useState } from 'react'
import { useQuery } from 'react-query'
import api from '../../lib/api'
import { format } from 'date-fns'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts'
import { getDesignationLabel } from '../../lib/topics'
import { Users, ClipboardList, TrendingUp, Award, Download, Activity } from 'lucide-react'
import { AttemptDetailsModal, DistrictDetailsModal } from './AdminDetailModals'

const COLORS = ['#185FA5','#639922','#BA7517','#D85A30','#7B6EBF','#2A9D8F']

export default function AdminDashboard() {
  const [selectedAttemptId, setSelectedAttemptId] = useState(null)
  const [selectedDistrict, setSelectedDistrict] = useState(null)

  const { data: stats, isLoading } = useQuery('admin-stats', async () => {
    const { data } = await api.get('/api/admin/stats')
    return data
  }, { refetchInterval: 60000 })

  const handleExportExcel = async () => {
    try {
      const res = await api.get('/api/admin/export/excel', { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'rescue1122_results.xlsx')
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (e) {
      console.error('Export Excel failed', e)
      alert('Failed to download Excel file')
    }
  }

  const handleExportPdf = async () => {
    try {
      const res = await api.get('/api/admin/export/pdf', { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'rescue1122_report.pdf')
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (e) {
      console.error('Export PDF failed', e)
      alert('Failed to download PDF file')
    }
  }

  if (isLoading) return (
    <div style={{ display: 'flex', justifyContent: 'center', paddingTop: '4rem' }}>
      <div className="spinner" />
    </div>
  )

  const topicChart = (stats?.topic_breakdown || []).slice(0, 8).map(t => ({
    name: t.topic.length > 22 ? t.topic.slice(0, 22) + '…' : t.topic,
    avg: t.avg_score,
    total: t.total,
  }))

  const passFailData = [
    { name: 'Passed', value: Math.round((stats?.pass_rate || 0) / 100 * (stats?.total_tests || 0)) },
    { name: 'Failed', value: Math.round((1 - (stats?.pass_rate || 0) / 100) * (stats?.total_tests || 0)) },
  ]
  const activityLog = stats?.activity_log || []

  return (
    <div className="fade-in">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h2>Dashboard</h2>
          <p style={{ color: 'var(--gray-300)', fontSize: '0.85rem', marginTop: 2 }}>Punjab Emergency Service · Rescue 1122 · All Districts</p>
        </div>
        <div className="responsive-actions" style={{ gap: '0.5rem' }}>
          <button className="btn btn-secondary btn-sm" onClick={handleExportExcel}><Download size={14} /> Excel</button>
          <button className="btn btn-secondary btn-sm" onClick={handleExportPdf}><Download size={14} /> PDF</button>
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
        {[
          { label: 'Total Staff',       value: stats?.total_staff   || 0, icon: <Users size={18} />,        color: 'var(--blue-700)',  sub: 'registered accounts' },
          { label: 'Total Tests',       value: stats?.total_tests   || 0, icon: <ClipboardList size={18} />,color: 'var(--amber-700)', sub: `${stats?.tests_this_month || 0} this month` },
          { label: 'Pass Rate',         value: `${stats?.pass_rate  || 0}%`,icon: <Award size={18} />,      color: 'var(--green-700)', sub: 'overall passing rate' },
          { label: 'Average Score',     value: `${stats?.avg_score  || 0}%`,icon: <TrendingUp size={18} />, color: 'var(--blue-500)',  sub: 'across all topics' },
        ].map(s => (
          <div key={s.label} className="stat-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div className="stat-label">{s.label}</div>
                <div className="stat-value" style={{ color: s.color }}>{s.value}</div>
                <div className="stat-sub">{s.sub}</div>
              </div>
              <div style={{ color: s.color, opacity: 0.35 }}>{s.icon}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="chart-grid">
        {/* Bar chart - avg score by topic */}
        <div className="card">
          <h4 style={{ marginBottom: '1rem' }}>Average Score by Topic</h4>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={topicChart} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--gray-300)' }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'var(--gray-300)' }} />
              <Tooltip formatter={(v) => [`${v}%`, 'Avg Score']} contentStyle={{ borderRadius: 8, border: '1px solid var(--gray-100)', fontSize: '0.8rem' }} />
              <Bar dataKey="avg" fill="var(--blue-500)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Pie chart - pass/fail */}
        <div className="card">
          <h4 style={{ marginBottom: '1rem' }}>Pass / Fail Ratio</h4>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={passFailData} cx="50%" cy="50%" innerRadius={55} outerRadius={80} dataKey="value" paddingAngle={3}>
                <Cell fill="var(--green-500)" />
                <Cell fill="var(--red-500)" />
              </Pie>
              <Legend iconType="circle" iconSize={10} wrapperStyle={{ fontSize: '0.8rem' }} />
              <Tooltip formatter={(v) => [v, 'Tests']} contentStyle={{ borderRadius: 8, fontSize: '0.8rem' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* District breakdown */}
      {stats?.question_bank_breakdown?.length > 0 && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <h4 style={{ marginBottom: '1rem' }}>Question Bank Coverage</h4>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Topic</th>
                  <th>Total MCQs</th>
                  <th>Easy</th>
                  <th>Medium</th>
                  <th>Hard</th>
                </tr>
              </thead>
              <tbody>
                {stats.question_bank_breakdown.map(topic => (
                  <tr key={topic.topic_id}>
                    <td style={{ fontWeight: 600 }}>{topic.topic}</td>
                    <td><strong>{topic.total}</strong></td>
                    <td><span className="badge badge-pass">{topic.easy}</span></td>
                    <td><span className="badge badge-blue">{topic.medium}</span></td>
                    <td><span className="badge badge-amber">{topic.hard}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* District breakdown */}
      {stats?.district_breakdown?.length > 0 && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <h4 style={{ marginBottom: '1rem' }}>Performance by District</h4>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>District</th>
                  <th>Tests Taken</th>
                  <th>Avg Score</th>
                  <th>Performance</th>
                </tr>
              </thead>
              <tbody>
                {stats.district_breakdown.map((d, i) => (
                  <tr className="interactive-row" key={i} onClick={() => setSelectedDistrict(d.district)} title="Click to view district details">
                    <td style={{ fontWeight: 500 }}>{d.district}</td>
                    <td>{d.tests}</td>
                    <td>
                      <strong style={{ color: d.avg_score >= 60 ? 'var(--green-700)' : 'var(--red-700)' }}>
                        {d.avg_score}%
                      </strong>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div className="progress-track" style={{ width: 100 }}>
                          <div className="progress-bar" style={{ width: `${d.avg_score}%`, background: d.avg_score >= 60 ? 'var(--green-500)' : 'var(--red-500)' }} />
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recent activity */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="section-row" style={{ marginBottom: '1rem' }}>
          <h4>Activity Log</h4>
          <span className="badge badge-blue">{activityLog.length} recent events</span>
        </div>
        {activityLog.length === 0 ? (
          <div style={{ padding: '1rem', color: 'var(--gray-400)', fontSize: '0.9rem' }}>No account or test activity recorded yet.</div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr><th>Event</th><th>Actor</th><th>Type</th><th>Time</th></tr>
              </thead>
              <tbody>
                {activityLog.slice(0, 12).map(log => (
                  <tr key={log.id}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span className="mini-avatar" style={{ width: 28, height: 28 }}><Activity size={14} /></span>
                        <span style={{ fontWeight: 600 }}>{log.description}</span>
                      </div>
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.78rem' }}>{log.actor_name || 'system'}</td>
                    <td><span className="badge badge-amber">{String(log.action || '').replaceAll('_', ' ')}</span></td>
                    <td style={{ fontSize: '0.78rem', color: 'var(--gray-300)' }}>{log.created_at ? format(new Date(log.created_at), 'dd MMM HH:mm') : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {stats?.recent_attempts?.length > 0 && (
        <div className="card">
          <h4 style={{ marginBottom: '1rem' }}>Recent Test Attempts</h4>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr><th>Staff</th><th>Designation</th><th>District</th><th>Topic</th><th>Score</th><th>Result</th><th>Date</th></tr>
              </thead>
              <tbody>
                {stats.recent_attempts.map(a => (
                  <tr className="interactive-row" key={a.id} onClick={() => setSelectedAttemptId(a.id)} title="Click to view attempt details">
                    <td style={{ fontWeight: 500 }}>{a.staff_name}</td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>{getDesignationLabel(a.designation)}</td>
                    <td>{a.district}</td>
                    <td style={{ fontSize: '0.8rem' }}>{a.topic}</td>
                    <td><strong style={{ color: a.passed ? 'var(--green-700)' : 'var(--red-700)' }}>{a.score.toFixed(0)}%</strong></td>
                    <td><span className={`badge ${a.passed ? 'badge-pass' : 'badge-fail'}`}>{a.passed ? 'Pass' : 'Fail'}</span></td>
                    <td style={{ fontSize: '0.78rem', color: 'var(--gray-300)' }}>{a.date ? format(new Date(a.date), 'dd MMM HH:mm') : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {selectedDistrict && (
        <DistrictDetailsModal district={selectedDistrict} onClose={() => setSelectedDistrict(null)} />
      )}
      {selectedAttemptId && (
        <AttemptDetailsModal attemptId={selectedAttemptId} onClose={() => setSelectedAttemptId(null)} />
      )}
    </div>
  )
}
