import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, KeyRound, Save } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'

const initialForm = {
  current_password: '',
  new_password: '',
  confirm_password: '',
}

function PasswordInput({ label, value, onChange, visible, onToggle, autoComplete }) {
  return (
    <div className="form-group">
      <label className="form-label">{label}</label>
      <div className="input-action-wrap">
        <input
          className="form-input"
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          autoComplete={autoComplete}
          required
        />
        <button type="button" className="input-action-btn" onClick={onToggle} aria-label={visible ? 'Hide password' : 'Show password'}>
          {visible ? <EyeOff size={17} /> : <Eye size={17} />}
        </button>
      </div>
    </div>
  )
}

export default function ChangePasswordPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [visible, setVisible] = useState({
    current_password: false,
    new_password: false,
    confirm_password: false,
  })
  const [saving, setSaving] = useState(false)

  const set = (key, value) => setForm(current => ({ ...current, [key]: value }))
  const toggle = key => setVisible(current => ({ ...current, [key]: !current[key] }))

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!form.current_password || !form.new_password || !form.confirm_password) {
      toast.error('Please fill all password fields.')
      return
    }
    if (form.new_password.length < 6) {
      toast.error('New password must be at least 6 characters.')
      return
    }
    if (form.new_password !== form.confirm_password) {
      toast.error('New password and confirm password do not match.')
      return
    }

    setSaving(true)
    try {
      await api.post('/api/auth/change-password', {
        current_password: form.current_password,
        new_password: form.new_password,
      })
      toast.success('Password changed successfully.')
      setForm(initialForm)
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Unable to change password.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page-content fade-in">
      <div style={{ marginBottom: '1.25rem' }}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <KeyRound size={22} /> Change Password
        </h2>
        <p style={{ color: 'var(--gray-300)', fontSize: '0.9rem', marginTop: 4 }}>
          Update your login password for this account.
        </p>
      </div>

      <div className="card" style={{ maxWidth: 540 }}>
        <form onSubmit={handleSubmit}>
          <PasswordInput
            label="Current Password"
            value={form.current_password}
            visible={visible.current_password}
            onToggle={() => toggle('current_password')}
            onChange={event => set('current_password', event.target.value)}
            autoComplete="current-password"
          />
          <PasswordInput
            label="New Password"
            value={form.new_password}
            visible={visible.new_password}
            onToggle={() => toggle('new_password')}
            onChange={event => set('new_password', event.target.value)}
            autoComplete="new-password"
          />
          <PasswordInput
            label="Confirm New Password"
            value={form.confirm_password}
            visible={visible.confirm_password}
            onToggle={() => toggle('confirm_password')}
            onChange={event => set('confirm_password', event.target.value)}
            autoComplete="new-password"
          />

          <div className="responsive-actions" style={{ marginTop: '1rem' }}>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? <><span className="spinner spinner-sm" /> Saving...</> : <><Save size={16} /> Save Password</>}
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => navigate(-1)} disabled={saving}>
              Back
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
