import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import { useEffect } from 'react'

export default function Layout() {
  const { user, fetchMe, logout } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => { fetchMe() }, [fetchMe])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="text-indigo-600 font-bold text-lg">MOF Jobs</Link>
          <nav className="flex items-center gap-6 text-sm">
            <Link to="/jobs" className="text-gray-600 hover:text-indigo-600">Jobs</Link>
            {user ? (
              <>
                <Link to="/profile" className="text-gray-600 hover:text-indigo-600">Profile</Link>
                {user.role === 'employer' && (
                  <Link to="/employer" className="text-gray-600 hover:text-indigo-600">Dashboard</Link>
                )}
                {user.role === 'admin' && (
                  <Link to="/admin" className="text-gray-600 hover:text-indigo-600">Admin</Link>
                )}
                <button onClick={handleLogout} className="text-gray-600 hover:text-red-500">Logout</button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-gray-600 hover:text-indigo-600">Login</Link>
                <Link to="/register" className="bg-indigo-600 text-white px-4 py-1.5 rounded-lg hover:bg-indigo-700">Sign Up</Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="bg-gray-800 text-gray-400 text-center py-6 text-sm">
        © {new Date().getFullYear()} MOF Engineering — Jobs Portal
      </footer>
    </div>
  )
}
