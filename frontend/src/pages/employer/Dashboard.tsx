import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../../lib/api'

interface EmployerStats {
  active_jobs: number
  total_applications: number
  pending_review: number
  hired: number
}

export default function EmployerDashboard() {
  const [stats, setStats] = useState<EmployerStats | null>(null)

  useEffect(() => {
    api.get<EmployerStats>('/employer/pipeline').then((r) => {
      // compute stats from pipeline or use a dedicated endpoint
      setStats(r.data as unknown as EmployerStats)
    }).catch(() => setStats({ active_jobs: 0, total_applications: 0, pending_review: 0, hired: 0 }))
  }, [])

  const cards = [
    { label: 'Active Jobs', value: stats?.active_jobs ?? '—', icon: '💼' },
    { label: 'Applications', value: stats?.total_applications ?? '—', icon: '📋' },
    { label: 'Under Review', value: stats?.pending_review ?? '—', icon: '⌛' },
    { label: 'Hired', value: stats?.hired ?? '—', icon: '🏆' },
  ]

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold">Employer Dashboard</h1>
        <Link to="/employer/jobs" className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm hover:bg-indigo-700">+ Post a Job</Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {cards.map((c) => (
          <div key={c.label} className="bg-white border border-gray-200 rounded-xl p-5">
            <div className="text-2xl mb-2">{c.icon}</div>
            <div className="text-3xl font-bold text-gray-900">{c.value}</div>
            <div className="text-sm text-gray-500">{c.label}</div>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Link to="/employer/jobs" className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md transition-shadow">
          <h2 className="text-base font-semibold mb-1">Manage Jobs</h2>
          <p className="text-sm text-gray-500">View and edit your job postings, pause or close roles.</p>
        </Link>
        <a href="/employer/candidates" className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md transition-shadow">
          <h2 className="text-base font-semibold mb-1">Find Talent</h2>
          <p className="text-sm text-gray-500">Search the candidate database and shortlist profiles.</p>
        </a>
      </div>
    </div>
  )
}
