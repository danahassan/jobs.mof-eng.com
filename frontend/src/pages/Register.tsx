import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../lib/api'
import { useAuthStore } from '../store/auth'

export default function Register() {
  const navigate = useNavigate()
  const fetchMe = useAuthStore((s) => s.fetchMe)
  const [isEmployer, setIsEmployer] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    const fd = new FormData(e.currentTarget)
    try {
      await api.post('/auth/register', {
        full_name: fd.get('full_name'),
        email: fd.get('email'),
        password: fd.get('password'),
        phone: fd.get('phone'),
        is_employer: isEmployer,
        company_name: isEmployer ? fd.get('company_name') : undefined,
      })
      await fetchMe()
      navigate(isEmployer ? '/employer' : '/')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error
      setError(msg || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-8">
      <div className="w-full max-w-md">
        <h1 className="text-2xl font-bold text-center mb-6">Join MOF Jobs</h1>

        {/* Role toggle */}
        <div className="flex bg-gray-100 rounded-xl p-1 mb-6 gap-1">
          <button type="button" onClick={() => setIsEmployer(false)}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${!isEmployer ? 'bg-white shadow text-indigo-600' : 'text-gray-500'}`}>
            👤 I'm a Candidate
          </button>
          <button type="button" onClick={() => setIsEmployer(true)}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${isEmployer ? 'bg-white shadow text-indigo-600' : 'text-gray-500'}`}>
            🏢 I'm an Employer
          </button>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl p-8">
          {error && <div className="bg-red-50 text-red-600 text-sm p-3 rounded-lg mb-5">{error}</div>}
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
              <input name="full_name" required placeholder="Ahmad Hassan"
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            {isEmployer && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Company Name</label>
                <input name="company_name" required={isEmployer} placeholder="Your company"
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input name="email" type="email" required placeholder="you@example.com"
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Phone (optional)</label>
              <input name="phone" placeholder="+964 ..."
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input name="password" type="password" required minLength={8} placeholder="Min. 8 characters"
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <button type="submit" disabled={loading}
              className="w-full bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-60">
              {loading ? 'Creating…' : isEmployer ? 'Create Employer Account' : 'Create Account'}
            </button>
          </form>
          <p className="text-center text-sm text-gray-500 mt-5">
            Already have an account? <Link to="/login" className="text-indigo-600">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
