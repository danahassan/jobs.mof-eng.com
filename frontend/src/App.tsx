import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/auth'
import Layout from './components/Layout'
import Home from './pages/Home'
import Jobs from './pages/Jobs'
import JobDetail from './pages/JobDetail'
import Login from './pages/Login'
import Register from './pages/Register'
import Profile from './pages/Profile'
import EmployerDashboard from './pages/employer/Dashboard'
import EmployerJobs from './pages/employer/Jobs'
import AdminDashboard from './pages/admin/Dashboard'

function PrivateRoute({ children, roles }: { children: JSX.Element; roles?: string[] }) {
  const user = useAuthStore((s) => s.user)
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="jobs" element={<Jobs />} />
          <Route path="jobs/:id" element={<JobDetail />} />
          <Route path="login" element={<Login />} />
          <Route path="register" element={<Register />} />
          <Route path="profile" element={<PrivateRoute><Profile /></PrivateRoute>} />
          <Route path="employer" element={<PrivateRoute roles={['employer']}><EmployerDashboard /></PrivateRoute>} />
          <Route path="employer/jobs" element={<PrivateRoute roles={['employer']}><EmployerJobs /></PrivateRoute>} />
          <Route path="admin" element={<PrivateRoute roles={['admin']}><AdminDashboard /></PrivateRoute>} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
