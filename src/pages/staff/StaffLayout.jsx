import { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { getDesignationLabel } from '../../lib/topics'
import { LayoutDashboard, BookOpen, ClipboardList, LogOut, PanelLeftClose, PanelLeftOpen, UserCheck } from 'lucide-react'

export default function StaffLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(true)
  const profile = user?.profile
  const designationLabel = getDesignationLabel(profile?.designation)

  const handleLogout = () => { logout(); navigate('/login') }

  const navItems = [
    { to: '/staff', label: 'Dashboard', icon: <LayoutDashboard size={16} />, end: true, mobileLabel: 'Home' },
    { to: '/staff/topics', label: 'Take Examination', icon: <BookOpen size={16} />, mobileLabel: 'Exam' },
    { to: '/staff/history', label: 'My Results', icon: <ClipboardList size={16} />, mobileLabel: 'Results' },
  ]

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <nav className="navbar">
        <NavLink to="/staff" className="navbar-brand">
          <img className="navbar-logo" src="/Mono.png" alt="Rescue 1122 monogram" />
          <span>Rescue 1122 — Staff Practice Portal</span>
          <span className="navbar-badge" style={{ background: 'rgba(255,255,255,0.15)', color: '#fff', fontSize: '0.7rem', fontWeight: 600, padding: '2px 8px', borderRadius: 99, marginLeft: 4 }}>
            <UserCheck size={10} style={{ display: 'inline', marginRight: 3 }} />STAFF
          </span>
        </NavLink>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div className="navbar-user" style={{ textAlign: 'right', marginRight: 8 }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#fff' }}>{profile?.full_name || user?.username}</div>
            <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.6)' }}>{designationLabel} · {profile?.district}</div>
          </div>
          <button className="btn btn-ghost btn-sm" style={{ color: 'rgba(255,255,255,0.75)' }} onClick={handleLogout}>
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </nav>

      <div className={`admin-layout ${menuOpen ? '' : 'admin-layout-collapsed'}`}>
        <aside className="sidebar">
          <div className="sidebar-top">
            <span className="sidebar-title">Staff Menu</span>
            <button className="btn btn-icon btn-secondary sidebar-toggle" onClick={() => setMenuOpen(open => !open)} title={menuOpen ? 'Close staff menu' : 'Open staff menu'}>
              {menuOpen ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
            </button>
          </div>
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `sidebar-item ${isActive ? 'active' : ''}`}
            >
              {item.icon} <span className="sidebar-label">{item.label}</span>
            </NavLink>
          ))}
        </aside>

        <main className="main-content staff-main">
          <Outlet />
        </main>
      </div>

      <nav className="mobile-tabbar" aria-label="Staff navigation">
        {navItems.map(item => (
          <NavLink key={item.to} to={item.to} end={item.end}>
            {item.icon}
            <span>{item.mobileLabel}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
