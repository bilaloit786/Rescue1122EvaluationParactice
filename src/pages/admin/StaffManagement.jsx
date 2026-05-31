import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import api from '../../lib/api'
import { DESIGNATIONS, DISTRICTS, getDesignationLabel } from '../../lib/topics'
import { format } from 'date-fns'
import { UserPlus, Trash2, X, Search, Eye, FileText, Download, Activity, CheckCircle2, XCircle, Clock, Mail, Phone, MapPin, User, Pencil } from 'lucide-react'
import toast from 'react-hot-toast'

function AddStaffModal({ onClose, onSuccess }) {
  const [form, setForm] = useState({ full_name:'', father_name:'', email:'', username:'', password:'', designation:'', district:'', station:'', employee_id:'', phone:'' })
  const [loading, setLoading] = useState(false)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/api/admin/staff', form)
      toast.success('Staff account created')
      onSuccess()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create staff')
    } finally { setLoading(false) }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
      <div className="card" style={{ width: '100%', maxWidth: 560, maxHeight: '90vh', overflowY: 'auto', borderRadius: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h3>Add New Staff Member</h3>
          <button className="btn btn-icon btn-secondary" onClick={onClose}><X size={16} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="responsive-form-grid" style={{ gap: '0.85rem' }}>
            {[
              { key: 'full_name',   label: 'Full Name *',      req: true },
              { key: 'father_name', label: "Father's Name",     req: false },
              { key: 'email',       label: 'Email *',           req: true, type: 'email' },
              { key: 'phone',       label: 'Phone',             req: false },
              { key: 'username',    label: 'Username *',        req: true },
              { key: 'password',    label: 'Password *',        req: true, type: 'password' },
              { key: 'station',     label: 'Station',           req: false },
              { key: 'employee_id', label: 'Employee ID',       req: false },
            ].map(f => (
              <div key={f.key} className="form-group" style={{ margin: 0 }}>
                <label className="form-label">{f.label}</label>
                <input className="form-input" type={f.type || 'text'} required={f.req} value={form[f.key]} onChange={e => set(f.key, e.target.value)} />
              </div>
            ))}
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Designation *</label>
              <select className="form-select" required value={form.designation} onChange={e => set('designation', e.target.value)}>
                <option value="">— Select —</option>
                {DESIGNATIONS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
              </select>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">District *</label>
              <select className="form-select" required value={form.district} onChange={e => set('district', e.target.value)}>
                <option value="">— Select —</option>
                {DISTRICTS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
          </div>
          <div className="responsive-actions" style={{ marginTop: '1.25rem' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <><span className="spinner spinner-sm" />Creating…</> : 'Create Account'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function EditStaffModal({ staff, onClose, onSuccess }) {
  const profile = staff?.profile || {}
  const [form, setForm] = useState({
    full_name: profile.full_name || '',
    father_name: profile.father_name || '',
    email: staff?.email || '',
    username: staff?.username || '',
    password: '',
    designation: profile.designation || '',
    district: profile.district || '',
    station: profile.station || '',
    employee_id: profile.employee_id || '',
    phone: profile.phone || '',
    is_active: Boolean(staff?.is_active),
  })
  const [loading, setLoading] = useState(false)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const payload = { ...form }
      if (!payload.password) delete payload.password
      await api.put(`/api/admin/staff/${staff.id}`, payload)
      toast.success('Staff account updated')
      onSuccess()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update staff')
    } finally { setLoading(false) }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
      <div className="card" style={{ width: '100%', maxWidth: 620, maxHeight: '90vh', overflowY: 'auto', borderRadius: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h3>Edit Registered User</h3>
          <button className="btn btn-icon btn-secondary" onClick={onClose}><X size={16} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="responsive-form-grid" style={{ gap: '0.85rem' }}>
            {[
              { key: 'full_name', label: 'Full Name *', req: true },
              { key: 'father_name', label: "Father's Name" },
              { key: 'email', label: 'Email *', req: true, type: 'email' },
              { key: 'phone', label: 'Phone' },
              { key: 'username', label: 'Username *', req: true },
              { key: 'password', label: 'New Password', type: 'password', placeholder: 'Leave blank to keep current' },
              { key: 'station', label: 'Station' },
              { key: 'employee_id', label: 'Employee ID' },
            ].map(f => (
              <div key={f.key} className="form-group" style={{ margin: 0 }}>
                <label className="form-label">{f.label}</label>
                <input className="form-input" type={f.type || 'text'} required={f.req} placeholder={f.placeholder || ''} value={form[f.key]} onChange={e => set(f.key, e.target.value)} />
              </div>
            ))}
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Designation *</label>
              <select className="form-select" required value={form.designation} onChange={e => set('designation', e.target.value)}>
                <option value="">— Select —</option>
                {DESIGNATIONS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
              </select>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">District *</label>
              <select className="form-select" required value={form.district} onChange={e => set('district', e.target.value)}>
                <option value="">— Select —</option>
                {DISTRICTS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <label style={{ gridColumn: '1 / -1', display: 'flex', alignItems: 'center', gap: 10, fontSize: '0.86rem', color: 'var(--gray-700)' }}>
              <input type="checkbox" checked={form.is_active} onChange={e => set('is_active', e.target.checked)} />
              Active login account
            </label>
          </div>
          <div className="responsive-actions" style={{ marginTop: '1.25rem' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <><span className="spinner spinner-sm" />Saving…</> : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function formatSafeDate(value, pattern = 'dd MMM yyyy') {
  if (!value) return '—'
  return format(new Date(value), pattern)
}

function shortUserAgent(value = '') {
  if (!value || value === 'Unknown') return 'Unknown'
  if (value.includes('Chrome')) return 'Chrome / Android or Desktop'
  if (value.includes('Firefox')) return 'Firefox'
  if (value.includes('Safari') && !value.includes('Chrome')) return 'Safari'
  if (value.includes('Edg')) return 'Microsoft Edge'
  return value.slice(0, 42)
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
        <div className="detail-value">{value || '—'}</div>
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

export function StaffDetailsModal({ staff, onClose }) {
  const { data, isLoading } = useQuery(
    ['staff-details', staff?.id],
    async () => {
      const { data } = await api.get(`/api/admin/staff/${staff.id}/details`)
      return data
    },
    { enabled: Boolean(staff?.id) }
  )

  const profile = data?.staff?.profile || staff?.profile || {}
  const stats = data?.stats || {}
  const attempts = data?.attempts || []
  const activity = data?.activity || []
  const access = data?.staff?.access || staff?.access || {}
  const name = profile.full_name || staff?.username

  const handlePdf = async () => {
    try {
      const res = await api.get(`/api/admin/staff/${staff.id}/pdf`, { responseType: 'blob' })
      const safeName = (name || 'staff').toLowerCase().replace(/[^a-z0-9]+/g, '_')
      downloadBlob(res.data, `rescue1122_staff_${safeName}.pdf`)
      toast.success('PDF generated')
    } catch (err) {
      toast.error('Failed to generate PDF')
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="detail-modal fade-in" onClick={e => e.stopPropagation()}>
        <div className="detail-hero">
          <button className="btn btn-icon btn-secondary detail-close" onClick={onClose} title="Close"><X size={16} /></button>
          <div className="avatar-mark">{(name || 'S').slice(0, 1).toUpperCase()}</div>
          <div style={{ minWidth: 0 }}>
            <h3>{name || 'Staff Member'}</h3>
            <p>{getDesignationLabel(profile.designation)} · {profile.district || 'District not set'}</p>
            <div className="detail-pills">
              <span className="badge badge-blue">@{staff.username}</span>
              <span className={`badge ${staff.is_active ? 'badge-pass' : 'badge-fail'}`}>{staff.is_active ? 'Active Login' : 'Inactive'}</span>
            </div>
          </div>
        </div>

        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}><div className="spinner" style={{ margin: '0 auto' }} /></div>
        ) : (
          <>
            <div className="metric-grid">
              <MetricTile label="Tests" value={stats.total_tests || 0} tone="blue" />
              <MetricTile label="Average" value={`${(stats.avg_score || 0).toFixed(1)}%`} tone="green" />
              <MetricTile label="Pass Rate" value={`${(stats.pass_rate || 0).toFixed(1)}%`} tone="amber" />
              <MetricTile label="Best Score" value={`${(stats.best_score || 0).toFixed(1)}%`} tone="red" />
            </div>

            <div className="detail-section">
              <h4>Login, Profile & Access Details</h4>
              <div className="detail-grid">
                <DetailItem icon={<User size={16} />} label="Father Name" value={profile.father_name} />
                <DetailItem icon={<Mail size={16} />} label="Email" value={data?.staff?.email || staff.email} />
                <DetailItem icon={<Phone size={16} />} label="Phone" value={profile.phone} />
                <DetailItem icon={<MapPin size={16} />} label="Station" value={profile.station} />
                <DetailItem icon={<FileText size={16} />} label="Employee ID" value={profile.employee_id} />
                <DetailItem icon={<Clock size={16} />} label="Joined" value={formatSafeDate(data?.staff?.created_at || staff.created_at)} />
                <DetailItem icon={<Activity size={16} />} label="Last IP Address" value={access.ip_address} />
                <DetailItem icon={<MapPin size={16} />} label="Last Location" value={access.location} />
                <DetailItem icon={<Clock size={16} />} label="Last Access" value={formatSafeDate(access.created_at, 'dd MMM yy, HH:mm')} />
              </div>
            </div>

            <div className="detail-section">
              <h4>Recent Login & Account Activity</h4>
              {activity.length === 0 ? (
                <div className="empty-detail">No login or account access activity recorded yet.</div>
              ) : (
                <div className="attempt-list">
                  {activity.slice(0, 8).map(entry => (
                    <div className="attempt-card" key={entry.id}>
                      <div className="attempt-main">
                        <Activity size={16} />
                        <div>
                          <strong>{entry.description}</strong>
                          <span>{entry.ip_address || 'Unknown IP'} · {entry.location || 'Unknown location'}</span>
                          <span>{shortUserAgent(entry.user_agent)}</span>
                        </div>
                      </div>
                      <div className="attempt-score">
                        <span className="badge badge-blue">{String(entry.action || '').replaceAll('_', ' ')}</span>
                        <span>{formatSafeDate(entry.created_at, 'dd MMM yy, HH:mm')}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="detail-section">
              <div className="section-row">
                <h4>Recent Test Attempts</h4>
                <button className="btn btn-primary btn-sm" onClick={handlePdf}>
                  <Download size={14} /> Generate PDF
                </button>
              </div>
              {attempts.length === 0 ? (
                <div className="empty-detail">No test attempts recorded for this login.</div>
              ) : (
                <div className="attempt-list">
                  {attempts.slice(0, 5).map(attempt => (
                    <div className="attempt-card" key={attempt.id}>
                      <div className="attempt-main">
                        <Activity size={16} />
                        <div>
                          <strong>{attempt.topic_label}</strong>
                          <span>{formatSafeDate(attempt.completed_at, 'dd MMM yy, HH:mm')}</span>
                        </div>
                      </div>
                      <div className="attempt-score">
                        <strong style={{ color: attempt.passed ? 'var(--green-700)' : 'var(--red-700)' }}>{Number(attempt.score_percent || 0).toFixed(0)}%</strong>
                        <span>{attempt.correct_answers}/{attempt.total_questions}</span>
                        {attempt.passed ? <CheckCircle2 size={16} color="var(--green-700)" /> : <XCircle size={16} color="var(--red-700)" />}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default function StaffManagement() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [selectedStaff, setSelectedStaff] = useState(null)
  const [editingStaff, setEditingStaff] = useState(null)
  const [search, setSearch] = useState('')

  const { data: staff = [], isLoading } = useQuery('admin-staff', async () => {
    const { data } = await api.get('/api/admin/staff')
    return data
  })

  const deleteMutation = useMutation(
    (id) => api.delete(`/api/admin/staff/${id}`),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('admin-staff')
        queryClient.invalidateQueries('admin-stats')
        toast.success('Staff deleted')
      },
      onError: () => toast.error('Delete failed'),
    }
  )

  const handleDelete = (s, event) => {
    event?.stopPropagation()
    if (window.confirm(`Delete account for ${s.profile?.full_name || s.username}? This cannot be undone.`)) {
      deleteMutation.mutate(s.id)
    }
  }

  const handleEdit = (s, event) => {
    event?.stopPropagation()
    setEditingStaff(s)
  }

  const filtered = staff.filter(s => {
    const q = search.toLowerCase()
    return !q || s.profile?.full_name?.toLowerCase().includes(q) || s.username?.toLowerCase().includes(q) || s.profile?.district?.toLowerCase().includes(q) || s.profile?.designation?.toLowerCase().includes(q)
  })

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h2>User Management</h2>
          <p style={{ color: 'var(--gray-300)', fontSize: '0.85rem', marginTop: 2 }}>{staff.length} registered users with login access</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <UserPlus size={15} /> Create User
        </button>
      </div>

      {/* Search */}
      <div className="mobile-full" style={{ position: 'relative', marginBottom: '1rem', maxWidth: 380 }}>
        <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--gray-300)' }} />
        <input className="form-input" style={{ paddingLeft: 36 }} placeholder="Search by name, district, designation…" value={search} onChange={e => setSearch(e.target.value)} />
      </div>

      <div className="card">
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '3rem' }}><div className="spinner" style={{ margin: '0 auto' }} /></div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--gray-300)' }}>No staff found</div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr><th>Name</th><th>Designation</th><th>District</th><th>Username</th><th>Last IP</th><th>Location</th><th>Last Access</th><th>Action</th></tr>
              </thead>
              <tbody>
                {filtered.map(s => (
                  <tr className="interactive-row" key={s.id} onClick={() => setSelectedStaff(s)} title="Click to view details">
                    <td>
                      <div className="login-name-cell">
                        <span className="mini-avatar">{(s.profile?.full_name || s.username || 'S').slice(0, 1).toUpperCase()}</span>
                        <span style={{ fontWeight: 600 }}>{s.profile?.full_name || '—'}</span>
                      </div>
                    </td>
                    <td><span className="badge badge-blue" style={{ fontSize: '0.72rem' }}>{getDesignationLabel(s.profile?.designation)}</span></td>
                    <td>{s.profile?.district || '—'}</td>
                    <td style={{ fontSize: '0.8rem', fontFamily: 'monospace' }}>{s.username}</td>
                    <td style={{ fontSize: '0.78rem', fontFamily: 'monospace' }}>{s.access?.ip_address || '—'}</td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--gray-400)' }}>{s.access?.location || '—'}</td>
                    <td style={{ fontSize: '0.78rem', color: 'var(--gray-300)' }}>{formatSafeDate(s.access?.created_at || s.created_at, 'dd MMM yy, HH:mm')}</td>
                    <td className="row-actions">
                      <button className="btn btn-icon btn-secondary" title="View details" onClick={(e) => { e.stopPropagation(); setSelectedStaff(s) }}>
                        <Eye size={14} />
                      </button>
                      <button className="btn btn-icon btn-secondary" title="Edit registered user" onClick={(e) => handleEdit(s, e)}>
                        <Pencil size={14} />
                      </button>
                      <button className="btn btn-icon btn-secondary" title="Delete" style={{ color: 'var(--red-700)' }} onClick={(e) => handleDelete(s, e)}>
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <AddStaffModal
          onClose={() => setShowModal(false)}
          onSuccess={() => {
            setShowModal(false)
            queryClient.invalidateQueries('admin-staff')
            queryClient.invalidateQueries('admin-stats')
          }}
        />
      )}
      {selectedStaff && (
        <StaffDetailsModal staff={selectedStaff} onClose={() => setSelectedStaff(null)} />
      )}
      {editingStaff && (
        <EditStaffModal
          staff={editingStaff}
          onClose={() => setEditingStaff(null)}
          onSuccess={() => {
            setEditingStaff(null)
            queryClient.invalidateQueries('admin-staff')
            queryClient.invalidateQueries(['staff-details', editingStaff.id])
            queryClient.invalidateQueries('admin-stats')
          }}
        />
      )}
    </div>
  )
}
