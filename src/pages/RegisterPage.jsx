import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../lib/api'
import { DESIGNATIONS, DISTRICTS } from '../lib/topics'
import toast from 'react-hot-toast'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    full_name: '', father_name: '', email: '', username: '', password: '',
    designation: '', district: '', station: '', employee_id: '', phone: '',
  })

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.full_name || !form.email || !form.username || !form.password || !form.designation || !form.district) {
      toast.error('Please fill all required fields'); return
    }
    setLoading(true)
    try {
      await api.post('/api/auth/register', form)
      toast.success('Account created! Please sign in.')
      navigate('/login')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed')
    } finally { setLoading(false) }
  }

  const inputProps = (key, type = 'text', placeholder = '', required = false) => ({
    className: 'form-input', type, placeholder, value: form[key], required,
    onChange: e => set(key, e.target.value)
  })

  return (
    <div className="auth-page" style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #042C53 0%, #185FA5 100%)', padding: '2rem', display: 'flex', alignItems: 'flex-start', justifyContent: 'center' }}>
      <div className="auth-shell" style={{ width: '100%', maxWidth: '560px', paddingTop: '2rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <img className="auth-logo-mark" src="/Mono.png" alt="Rescue 1122 monogram" style={{ margin: '0 auto 0.75rem' }} />
          <h1 className="auth-title" style={{ color: '#fff', fontSize: '1.25rem', fontWeight: 700 }}>Rescue 1122 — Staff Registration</h1>
          <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.85rem', marginTop: 4 }}>Create your evaluation portal account</p>
        </div>
        <div className="card auth-card" style={{ borderRadius: 16, padding: '2rem' }}>
          <form onSubmit={handleSubmit}>
            <div className="responsive-form-grid">
              <div className="form-group">
                <label className="form-label">Full Name *</label>
                <input {...inputProps('full_name', 'text', 'Muhammad Bilal', true)} />
              </div>
              <div className="form-group">
                <label className="form-label">Father's Name</label>
                <input {...inputProps('father_name', 'text', 'Muhammad Aslam')} />
              </div>
              <div className="form-group">
                <label className="form-label">Designation *</label>
                <select className="form-select" value={form.designation} required onChange={e => set('designation', e.target.value)}>
                  <option value="">— Select —</option>
                  {DESIGNATIONS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">District *</label>
                <select className="form-select" value={form.district} required onChange={e => set('district', e.target.value)}>
                  <option value="">— Select —</option>
                  {DISTRICTS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Station / Division</label>
                <input {...inputProps('station', 'text', 'e.g. Station A')} />
              </div>
              <div className="form-group">
                <label className="form-label">Employee ID</label>
                <input {...inputProps('employee_id', 'text', 'e.g. ESA-12345')} />
              </div>
              <div className="form-group">
                <label className="form-label">Email Address *</label>
                <input {...inputProps('email', 'email', 'you@rescue1122.gov.pk', true)} />
              </div>
              <div className="form-group">
                <label className="form-label">Phone</label>
                <input {...inputProps('phone', 'tel', '0300-0000000')} />
              </div>
              <div className="form-group">
                <label className="form-label">Username *</label>
                <input {...inputProps('username', 'text', 'choose a username', true)} />
              </div>
              <div className="form-group">
                <label className="form-label">Password *</label>
                <input {...inputProps('password', 'password', 'minimum 6 characters', true)} />
              </div>
            </div>
            <button className="btn btn-primary btn-block btn-lg" type="submit" disabled={loading} style={{ marginTop: '0.75rem' }}>
              {loading ? <><span className="spinner spinner-sm" />Creating account...</> : 'Create account →'}
            </button>
          </form>
          <p style={{ textAlign: 'center', marginTop: '1rem', fontSize: '0.85rem', color: 'var(--gray-500)' }}>
            Already registered? <Link to="/login" style={{ color: 'var(--blue-700)', fontWeight: 500, textDecoration: 'none' }}>Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
