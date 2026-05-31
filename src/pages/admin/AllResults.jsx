import { useState } from 'react'
import { useQuery } from 'react-query'
import api from '../../lib/api'
import { DISTRICTS, getDesignationLabel } from '../../lib/topics'
import { format } from 'date-fns'
import { Download, Filter } from 'lucide-react'
import { AttemptDetailsModal } from './AdminDetailModals'

export default function AllResults() {
  const [district, setDistrict] = useState('')
  const [topic, setTopic]       = useState('')
  const [passed, setPassed]     = useState('')
  const [selectedAttemptId, setSelectedAttemptId] = useState(null)

  const { data: results = [], isLoading } = useQuery(
    ['admin-results', district, topic, passed],
    async () => {
      const params = new URLSearchParams()
      if (district) params.set('district', district)
      if (topic)    params.set('topic', topic)
      if (passed !== '') params.set('passed', passed)
      const { data } = await api.get(`/api/admin/attempts?${params}`)
      return data
    }
  )

  const handleExportExcel = async () => {
    try {
      const params = new URLSearchParams()
      if (district) params.set('district', district)
      if (topic)    params.set('topic', topic)
      const res = await api.get(`/api/admin/export/excel?${params}`, { responseType: 'blob' })
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
      const params = new URLSearchParams()
      if (district) params.set('district', district)
      const res = await api.get(`/api/admin/export/pdf?${params}`, { responseType: 'blob' })
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

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h2>All Examination Results</h2>
          <p style={{ color: 'var(--gray-300)', fontSize: '0.85rem', marginTop: 2 }}>{results.length} records found</p>
        </div>
        <div className="responsive-actions" style={{ gap: '0.5rem' }}>
          <button className="btn btn-secondary btn-sm" onClick={handleExportExcel}><Download size={14} /> Excel</button>
          <button className="btn btn-secondary btn-sm" onClick={handleExportPdf}><Download size={14} /> PDF</button>
        </div>
      </div>

      {/* Filters */}
      <div className="card card-sm mobile-stack" style={{ marginBottom: '1rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <Filter size={15} color="var(--gray-300)" style={{ alignSelf: 'center' }} />
        <div className="form-group mobile-full" style={{ margin: 0, minWidth: 160 }}>
          <label className="form-label">District</label>
          <select className="form-select" value={district} onChange={e => setDistrict(e.target.value)}>
            <option value="">All Districts</option>
            {DISTRICTS.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div className="form-group mobile-full" style={{ margin: 0, minWidth: 200 }}>
          <label className="form-label">Topic</label>
          <input className="form-input" placeholder="Filter by topic…" value={topic} onChange={e => setTopic(e.target.value)} />
        </div>
        <div className="form-group mobile-full" style={{ margin: 0 }}>
          <label className="form-label">Result</label>
          <select className="form-select" value={passed} onChange={e => setPassed(e.target.value)}>
            <option value="">All</option>
            <option value="true">Passed</option>
            <option value="false">Failed</option>
          </select>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={() => { setDistrict(''); setTopic(''); setPassed('') }}>Clear</button>
      </div>

      <div className="card">
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}><div className="spinner" style={{ margin: '0 auto' }} /></div>
        ) : results.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--gray-300)' }}>No results found</div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Name</th>
                  <th>Father</th>
                  <th>Designation</th>
                  <th>District</th>
                  <th>Topic</th>
                  <th>Score</th>
                  <th>Correct</th>
                  <th>Result</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => {
                  const p = r.user?.profile || {}
                  return (
                    <tr className="interactive-row" key={r.id} onClick={() => setSelectedAttemptId(r.id)} title="Click to view result details">
                      <td style={{ color: 'var(--gray-300)', fontSize: '0.78rem' }}>{i + 1}</td>
                      <td style={{ fontWeight: 500 }}>{p.full_name || '—'}</td>
                      <td style={{ color: 'var(--gray-400)', fontSize: '0.8rem' }}>{p.father_name || '—'}</td>
                      <td><span className="badge badge-blue" style={{ fontSize: '0.68rem' }}>{getDesignationLabel(p.designation)}</span></td>
                      <td>{p.district || '—'}</td>
                      <td style={{ fontSize: '0.8rem', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.topic_label}</td>
                      <td><strong style={{ color: r.passed ? 'var(--green-700)' : 'var(--red-700)' }}>{r.score_percent.toFixed(0)}%</strong></td>
                      <td style={{ textAlign: 'center' }}>{r.correct_answers}/{r.total_questions}</td>
                      <td><span className={`badge ${r.passed ? 'badge-pass' : 'badge-fail'}`}>{r.passed ? 'Pass' : 'Fail'}</span></td>
                      <td style={{ fontSize: '0.76rem', color: 'var(--gray-300)', whiteSpace: 'nowrap' }}>
                        {r.completed_at ? format(new Date(r.completed_at), 'dd MMM yy, HH:mm') : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {selectedAttemptId && (
        <AttemptDetailsModal attemptId={selectedAttemptId} onClose={() => setSelectedAttemptId(null)} />
      )}
    </div>
  )
}
