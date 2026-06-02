import { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { LayoutDashboard, Users, ClipboardList, Trophy, LogOut, Shield, Database, PanelLeftClose, PanelLeftOpen, BookMarked } from 'lucide-react'

export default function AdminLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(true)

  const handleLogout = () => { logout(); navigate('/login') }

  const navItems = [
    { to: '/admin',             label: 'Dashboard',      icon: <LayoutDashboard size={16} />, end: true, mobileLabel: 'Home' },
    { to: '/admin/staff',       label: 'User Management',  icon: <Users size={16} />, mobileLabel: 'Users' },
    { to: '/admin/results',     label: 'All Results',    icon: <ClipboardList size={16} />, mobileLabel: 'Results' },
    { to: '/admin/leaderboard', label: 'Leaderboard',    icon: <Trophy size={16} />, mobileLabel: 'Ranks' },
    { to: '/admin/question-bank', label: 'Question Bank', icon: <Database size={16} />, mobileLabel: 'Bank' },
    { to: '/admin/learning-material', label: 'Learning Material', icon: <BookMarked size={16} />, mobileLabel: 'Learn' },
  ]

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <nav className="navbar">
        <div className="navbar-brand">
          <img className="navbar-logo" src="/Mono.png" alt="Rescue 1122 monogram" />
          <span>Rescue 1122 — Admin Portal</span>
          <span className="navbar-badge" style={{ background: 'rgba(255,255,255,0.15)', color: '#fff', fontSize: '0.7rem', fontWeight: 600, padding: '2px 8px', borderRadius: 99, marginLeft: 4 }}>
            <Shield size={10} style={{ display: 'inline', marginRight: 3 }} />ADMIN
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="navbar-user" style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.75)' }}>{user?.username}</span>
          <button className="btn btn-ghost btn-sm" style={{ color: 'rgba(255,255,255,0.75)' }} onClick={handleLogout}>
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </nav>

      <div className={`admin-layout ${menuOpen ? '' : 'admin-layout-collapsed'}`}>
        <aside className="sidebar">
          <div className="sidebar-top">
            <span className="sidebar-title">Admin Menu</span>
            <button className="btn btn-icon btn-secondary sidebar-toggle" onClick={() => setMenuOpen(open => !open)} title={menuOpen ? 'Close admin menu' : 'Open admin menu'}>
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

        <main className="main-content">
          <Outlet />
        </main>
      </div>

      <nav className="mobile-tabbar" aria-label="Admin navigation">
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
