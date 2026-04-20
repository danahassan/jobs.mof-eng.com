import { useEffect, useState } from 'react'
import api from '../../lib/api'

interface AdminStats {
  total_users: number
  total_positions: number
  total_applications: number
  hired_this_month: number
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminStats | null>(null)

  useEffect(() => {
    api.get<AdminStats>('/admin/stats').then((r) => setStats(r.data))
  }, [])

  const cards = [
    { label: 'Total Users', value: stats?.total_users ?? '—', icon: '👥' },
    { label: 'Positions', value: stats?.total_positions ?? '—', icon: '📌' },
    { label: 'Applications', value: stats?.total_applications ?? '—', icon: '📄' },
    { label: 'Hired This Month', value: stats?.hired_this_month ?? '—', icon: '✅' },
  ]

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-8">Admin Dashboard</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {cards.map((c) => (
          <div key={c.label} className="bg-white border border-gray-200 rounded-xl p-5">
            <div className="text-2xl mb-2">{c.icon}</div>
            <div className="text-3xl font-bold">{c.value}</div>
            <div className="text-sm text-gray-500">{c.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
