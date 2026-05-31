import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'
import { Eye, EyeOff, RefreshCw, ShieldCheck, UserCheck } from 'lucide-react'

const CAPTCHA_WORDS = ['RESCUE', 'SAFETY', 'LADDER', 'WATER', 'ALARM', 'TRAIN']

function makeCaptcha() {
  return CAPTCHA_WORDS[Math.floor(Math.random() * CAPTCHA_WORDS.length)]
}

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', password: '' })
  const [captcha, setCaptcha] = useState(makeCaptcha)
  const [captchaInput, setCaptchaInput] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  const refreshCaptcha = () => {
    setCaptcha(makeCaptcha())
    setCaptchaInput('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.username || !form.password) { toast.error('Please fill all fields'); return }
    if (captchaInput.trim().toUpperCase() !== captcha) {
      toast.error('Please enter the English captcha correctly.')
      refreshCaptcha()
      return
    }
    setLoading(true)
    try {
      const user = await login(form.username, form.password)
      toast.success(`Welcome back, ${user.profile?.full_name || user.username}!`)
      navigate(user.role === 'admin' ? '/admin' : '/staff', { replace: true })
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed. Check credentials.')
      refreshCaptcha()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #042C53 0%, #185FA5 100%)', padding: '2rem' }}>
      <div className="auth-shell" style={{ width: '100%', maxWidth: '420px' }}>
        {/* Header */}
        <div className="auth-brand-row" style={{ marginBottom: '2rem' }}>
          <img className="auth-logo-mark" src="/Mono.png" alt="Rescue 1122 monogram" />
          <div>
            <h1 className="auth-title" style={{ color: '#fff', fontSize: '1.5rem', fontWeight: 700, marginBottom: 4 }}>Rescue 1122</h1>
            <p style={{ color: 'rgba(255,255,255,0.76)', fontSize: '0.95rem', fontWeight: 700 }}>Staff Practice Portal</p>
            <p style={{ color: 'rgba(255,255,255,0.62)', fontSize: '0.82rem' }}>Punjab Emergency Service</p>
          </div>
        </div>

        {/* Card */}
        <div className="card auth-card" style={{ borderRadius: 16, padding: '2rem' }}>
          <h2 style={{ marginBottom: '1.5rem', fontSize: '1.1rem', color: 'var(--gray-900)' }}>Sign in to your account</h2>
          <div className="login-access-grid" aria-label="Available login portals">
            <div className="login-access-chip">
              <UserCheck size={17} />
              <span>Staff Login</span>
            </div>
            <div className="login-access-chip">
              <ShieldCheck size={17} />
              <span>Admin Login</span>
            </div>
          </div>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Username</label>
              <input className="form-input" type="text" placeholder="Enter your username" value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} autoComplete="username" autoFocus />
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <div className="input-action-wrap">
                <input className="form-input" type={showPassword ? 'text' : 'password'} placeholder="Enter your password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} autoComplete="current-password" />
                <button type="button" className="input-action-btn" onClick={() => setShowPassword(show => !show)} aria-label={showPassword ? 'Hide password' : 'Show password'}>
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">English Captcha</label>
              <div className="captcha-row">
                <div className="captcha-code" aria-label="Captcha code">{captcha}</div>
                <button type="button" className="btn btn-icon btn-secondary" onClick={refreshCaptcha} title="Refresh captcha">
                  <RefreshCw size={16} />
                </button>
              </div>
              <input className="form-input" type="text" placeholder="Type the English word above" value={captchaInput} onChange={e => setCaptchaInput(e.target.value)} autoComplete="off" style={{ marginTop: 8 }} />
            </div>
            <button className="btn btn-primary btn-block btn-lg" type="submit" disabled={loading} style={{ marginTop: '0.5rem' }}>
              {loading ? <><span className="spinner spinner-sm" />Signing in...</> : 'Sign in →'}
            </button>
          </form>
          <p style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.85rem', color: 'var(--gray-500)' }}>
            New staff member?{' '}
            <Link to="/register" style={{ color: 'var(--blue-700)', fontWeight: 500, textDecoration: 'none' }}>Create account</Link>
          </p>
        </div>
        <p style={{ textAlign: 'center', color: 'rgba(255,255,255,0.4)', fontSize: '0.75rem', marginTop: '1.5rem' }}>
          Developed by Muhammad Bilal | This application is an hobby project and is not affiliated with or endorsed by Rescue 1122 or Emergency Services Academy.        </p>
      </div>
    </div>
  )
}
