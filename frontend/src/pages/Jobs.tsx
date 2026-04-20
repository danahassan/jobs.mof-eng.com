import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../lib/api'

interface Job {
  id: number
  title: string
  type: string
  location: string | null
  is_remote: boolean
  salary_min: number | null
  salary_max: number | null
  department: string | null
  created_at: string
  company_name: string | null
}

interface JobsResponse {
  jobs: Job[]
  total: number
  pages: number
  page: number
}

export default function Jobs() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [data, setData] = useState<JobsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const q = searchParams.get('q') || ''

  useEffect(() => {
    setLoading(true)
    api.get<JobsResponse>('/jobs', { params: Object.fromEntries(searchParams) })
      .then((r) => setData(r.data))
      .finally(() => setLoading(false))
  }, [searchParams])

  const handleSearch = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    setSearchParams({ q: fd.get('q') as string })
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Browse Jobs</h1>
      <form onSubmit={handleSearch} className="flex gap-3 mb-8">
        <input name="q" defaultValue={q} placeholder="Search by title, skill, location…"
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
        <button type="submit" className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700">Search</button>
      </form>

      {loading ? (
        <div className="text-center py-20 text-gray-400">Loading…</div>
      ) : !data?.jobs.length ? (
        <div className="text-center py-20 text-gray-400">No jobs found.</div>
      ) : (
        <div className="flex flex-col gap-4">
          {data.jobs.map((job) => (
            <div key={job.id} className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <Link to={`/jobs/${job.id}`} className="text-lg font-semibold text-gray-900 hover:text-indigo-600">{job.title}</Link>
                  <div className="text-sm text-gray-500 mt-1 flex gap-3 flex-wrap">
                    {job.company_name && <span>{job.company_name}</span>}
                    {job.location && <span>📍 {job.location}</span>}
                    <span>{job.type}</span>
                    {job.is_remote && <span className="text-purple-600">Remote</span>}
                  </div>
                </div>
                <Link to={`/jobs/${job.id}`}
                  className="border border-indigo-600 text-indigo-600 px-4 py-1.5 rounded-lg text-sm hover:bg-indigo-50 whitespace-nowrap">
                  View Job
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
