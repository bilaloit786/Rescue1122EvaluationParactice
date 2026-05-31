import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'

// Shared pages
import LoginPage        from './pages/LoginPage'
import RegisterPage     from './pages/RegisterPage'

// Staff pages
import StaffLayout      from './pages/staff/StaffLayout'
import StaffDashboard   from './pages/staff/StaffDashboard'
import TopicSelectPage  from './pages/staff/TopicSelectPage'
import ExamPage         from './pages/staff/ExamPage'
import ResultPage       from './pages/staff/ResultPage'
import HistoryPage      from './pages/staff/HistoryPage'

// Admin pages
import AdminLayout      from './pages/admin/AdminLayout'
import AdminDashboard   from './pages/admin/AdminDashboard'
import StaffManagement  from './pages/admin/StaffManagement'
import AllResults       from './pages/admin/AllResults'
import Leaderboard      from './pages/admin/Leaderboard'
import QuestionBank     from './pages/admin/QuestionBank'

function PrivateRoute({ children, role }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (role === 'admin' && user.role !== 'admin') return <Navigate to="/staff" replace />
  return children
}

function PublicRoute({ children }) {
  const { user } = useAuth()
  if (user) return <Navigate to={user.role === 'admin' ? '/admin' : '/staff'} replace />
  return children
}

function AppRoutes() {
  useEffect(() => {
    const refreshTimer = window.setInterval(() => {
      window.location.reload()
    }, 5 * 60 * 1000)

    return () => window.clearInterval(refreshTimer)
  }, [])

  return (
    <Routes>
      {/* Public */}
      <Route path="/login"    element={<PublicRoute><LoginPage /></PublicRoute>} />
      <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
      <Route path="/"         element={<Navigate to="/login" replace />} />

      {/* Staff portal */}
      <Route path="/staff" element={<PrivateRoute><StaffLayout /></PrivateRoute>}>
        <Route index          element={<StaffDashboard />} />
        <Route path="topics"  element={<TopicSelectPage />} />
        <Route path="exam"    element={<ExamPage />} />
        <Route path="result"  element={<ResultPage />} />
        <Route path="history" element={<HistoryPage />} />
      </Route>

      {/* Admin portal */}
      <Route path="/admin" element={<PrivateRoute role="admin"><AdminLayout /></PrivateRoute>}>
        <Route index         element={<AdminDashboard />} />
        <Route path="staff"  element={<StaffManagement />} />
        <Route path="results"element={<AllResults />} />
        <Route path="leaderboard" element={<Leaderboard />} />
        <Route path="question-bank" element={<QuestionBank />} />
      </Route>

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
