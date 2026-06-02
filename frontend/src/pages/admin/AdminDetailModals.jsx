import { useQuery } from 'react-query'
import api from '../../lib/api'
import { getDesignationLabel } from '../../lib/topics'
import { format } from 'date-fns'
import { X, Download, Activity, CheckCircle2, XCircle, Clock, Mail, MapPin, User, FileText, BarChart3 } from 'lucide-react'
import toast from 'react-hot-toast'

function formatSafeDate(value, pattern = 'dd MMM yyyy') {
  if (!value) return '-'
  return format(new Date(value), pattern)
}

function downloadBlob(data, filename) {
  const url = window.URL.createObjectURL(new Blob([data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

function DetailItem({ icon, label, value }) {
  return (
    <div className="detail-item">
      <div className="detail-icon">{icon}</div>
      <div>
        <div className="detail-label">{label}</div>
        <div className="detail-value">{value || '-'}</div>
      </div>
    </div>
  )
}

function MetricTile({ label, value, tone = 'blue' }) {
  return (
    <div className={`metric-tile metric-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

export function AttemptDetailsModal({ attemptId, onClose }) {
  const { data: attempt, isLoading } = useQuery(
    ['attempt-details', attemptId],
    async () => {
      const { data } = await api.get(`/api/admin/attempts/${attemptId}/details`)
      return data
    },
    { enabled: Boolean(attemptId) }
  )

  const profile = attempt?.user?.profile || {}
  const name = profile.full_name || attempt?.user?.username || 'Staff Member'
  const subtopics = Object.entries(attempt?.subtopic_scores || {})

  const handlePdf = async () => {
    try {
      const res = await api.get(`/api/admin/attempts/${attemptId}/pdf`, { responseType: 'blob' })
      const safeName = name.toLowerCase().replace(/[^a-z0-9]+/g, '_')
      downloadBlob(res.data, `rescue1122_attempt_${safeName}_${attemptId}.pdf`)
      toast.success('Attempt report generated')
    } catch (err) {
      toast.error('Failed to generate report')
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="detail-modal fade-in" onClick={e => e.stopPropagation()}>
        <div className="detail-hero">
          <button className="btn btn-icon btn-secondary detail-close" onClick={onClose} title="Close"><X size={16} /></button>
          <div className="avatar-mark"><FileText size={26} /></div>
          <div style={{ minWidth: 0 }}>
            <h3>Attempt Detail</h3>
            <p>{name} · {attempt?.topic_label || 'Loading...'}</p>
            {attempt && (
              <div className="detail-pills">
                <span className={`badge ${attempt.passed ? 'badge-pass' : 'badge-fail'}`}>{attempt.passed ? 'Passed' : 'Failed'}</span>
                <span className="badge badge-blue">{Number(attempt.score_percent || 0).toFixed(0)}%</span>
              </div>
            )}
          </div>
        </div>

        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}><div className="spinner" style={{ margin: '0 auto' }} /></div>
        ) : (
          <>
            <div className="metric-grid">
              <MetricTile label="Score" value={`${Number(attempt.score_percent || 0).toFixed(1)}%`} tone={attempt.passed ? 'green' : 'red'} />
              <MetricTile label="Correct" value={`${attempt.correct_answers}/${attempt.total_questions}`} tone="blue" />
              <MetricTile label="Time" value={`${Math.round((attempt.time_taken_seconds || 0) / 60)} min`} tone="amber" />
              <MetricTile label="Result" value={attempt.passed ? 'Pass' : 'Fail'} tone={attempt.passed ? 'green' : 'red'} />
            </div>

            <div className="detail-section">
              <h4>Staff & Exam Details</h4>
              <div className="detail-grid">
                <DetailItem icon={<User size={16} />} label="Staff" value={name} />
                <DetailItem icon={<Mail size={16} />} label="Email" value={attempt.user?.email} />
                <DetailItem icon={<MapPin size={16} />} label="District" value={profile.district} />
                <DetailItem icon={<Activity size={16} />} label="Designation" value={getDesignationLabel(profile.designation)} />
                <DetailItem icon={<FileText size={16} />} label="Topic" value={attempt.topic_label} />
                <DetailItem icon={<Clock size={16} />} label="Completed" value={formatSafeDate(attempt.completed_at, 'dd MMM yy, HH:mm')} />
              </div>
            </div>

            <div className="detail-section">
              <div className="section-row">
                <h4>Report Details</h4>
                <button className="btn btn-primary btn-sm" onClick={handlePdf}>
                  <Download size={14} /> Generate Report
                </button>
              </div>
              {subtopics.length > 0 && (
                <div className="attempt-list" style={{ marginBottom: '1rem' }}>
                  {subtopics.map(([topic, score]) => (
                    <div className="attempt-card" key={topic}>
                      <div className="attempt-main">
                        <BarChart3 size={16} />
                        <div>
                          <strong>{topic}</strong>
                          <span>{score.correct}/{score.total} correct</span>
                        </div>
                      </div>
                      <div className="attempt-score">
                        <strong>{Number(score.percent || 0).toFixed(1)}%</strong>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {attempt.ai_feedback ? (
                <div className="feedback-box">{attempt.ai_feedback}</div>
              ) : (
                <div className="empty-detail">No feedback recorded for this attempt.</div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export function DistrictDetailsModal({ district, onClose }) {
  const { data, isLoading } = useQuery(
    ['district-details', district],
    async () => {
      const { data } = await api.get(`/api/admin/districts/${encodeURIComponent(district)}/details`)
      return data
    },
    { enabled: Boolean(district) }
  )

  const stats = data?.stats || {}

  const handlePdf = async () => {
    try {
      const res = await api.get(`/api/admin/districts/${encodeURIComponent(district)}/pdf`, { responseType: 'blob' })
      const safeName = district.toLowerCase().replace(/[^a-z0-9]+/g, '_')
      downloadBlob(res.data, `rescue1122_district_${safeName}.pdf`)
      toast.success('District report generated')
    } catch (err) {
      toast.error('Failed to generate report')
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="detail-modal fade-in" onClick={e => e.stopPropagation()}>
        <div className="detail-hero">
          <button className="btn btn-icon btn-secondary detail-close" onClick={onClose} title="Close"><X size={16} /></button>
          <div className="avatar-mark"><MapPin size={26} /></div>
          <div style={{ minWidth: 0 }}>
            <h3>{district}</h3>
            <p>District performance summary</p>
            <div className="detail-pills">
              <span className="badge badge-blue">{stats.total_tests || 0} tests</span>
              <span className={`badge ${(stats.avg_score || 0) >= 60 ? 'badge-pass' : 'badge-fail'}`}>{Number(stats.avg_score || 0).toFixed(1)}% avg</span>
            </div>
          </div>
        </div>

        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}><div className="spinner" style={{ margin: '0 auto' }} /></div>
        ) : (
          <>
            <div className="metric-grid">
              <MetricTile label="Staff" value={stats.staff_count || 0} tone="blue" />
              <MetricTile label="Tests" value={stats.total_tests || 0} tone="amber" />
              <MetricTile label="Pass Rate" value={`${Number(stats.pass_rate || 0).toFixed(1)}%`} tone="green" />
              <MetricTile label="Average" value={`${Number(stats.avg_score || 0).toFixed(1)}%`} tone={(stats.avg_score || 0) >= 60 ? 'green' : 'red'} />
            </div>

            <div className="detail-section">
              <div className="section-row">
                <h4>Topic Breakdown</h4>
                <button className="btn btn-primary btn-sm" onClick={handlePdf}>
                  <Download size={14} /> Generate Report
                </button>
              </div>
              {data?.topics?.length ? (
                <div className="attempt-list">
                  {data.topics.slice(0, 6).map(topic => (
                    <div className="attempt-card" key={topic.topic}>
                      <div className="attempt-main">
                        <Activity size={16} />
                        <div>
                          <strong>{topic.topic}</strong>
                          <span>{topic.passed}/{topic.total} passed</span>
                        </div>
                      </div>
                      <div className="attempt-score">
                        <strong>{Number(topic.avg_score || 0).toFixed(1)}%</strong>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-detail">No examination data recorded for this district.</div>
              )}
            </div>

            <div className="detail-section">
              <h4>Recent Attempts</h4>
              <div className="attempt-list">
                {(data?.recent_attempts || []).slice(0, 5).map(attempt => {
                  const profile = attempt.user?.profile || {}
                  return (
                    <div className="attempt-card" key={attempt.id}>
                      <div className="attempt-main">
                        <Activity size={16} />
                        <div>
                          <strong>{profile.full_name || 'Staff Member'}</strong>
                          <span>{attempt.topic_label} · {formatSafeDate(attempt.completed_at, 'dd MMM yy, HH:mm')}</span>
                        </div>
                      </div>
                      <div className="attempt-score">
                        <strong style={{ color: attempt.passed ? 'var(--green-700)' : 'var(--red-700)' }}>{Number(attempt.score_percent || 0).toFixed(0)}%</strong>
                        {attempt.passed ? <CheckCircle2 size={16} color="var(--green-700)" /> : <XCircle size={16} color="var(--red-700)" />}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
