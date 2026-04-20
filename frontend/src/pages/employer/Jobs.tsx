import { useEffect, useState } from 'react'
import api from '../../lib/api'

interface Job {
  id: number
  title: string
  type: string
  is_active: boolean
  created_at: string
}

export default function EmployerJobs() {
  const [jobs, setJobs] = useState<Job[]>([])

  useEffect(() => {
    api.get<{ jobs: Job[] }>('/employer/jobs').then((r) => setJobs(r.data.jobs))
  }, [])

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">My Job Postings</h1>
        <a href="/employer/jobs/new" className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm hover:bg-indigo-700">+ New Job</a>
      </div>
      {!jobs.length ? (
        <div className="text-center py-20 text-gray-400">No jobs posted yet.</div>
      ) : (
        <div className="flex flex-col gap-3">
          {jobs.map((job) => (
            <div key={job.id} className="bg-white border border-gray-200 rounded-xl p-5 flex items-center justify-between gap-4 flex-wrap">
              <div>
                <div className="font-semibold text-gray-900">{job.title}</div>
                <div className="text-sm text-gray-500 mt-0.5">{job.type} · {job.created_at.slice(0,10)}</div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-xs px-3 py-1 rounded-full ${job.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                  {job.is_active ? 'Active' : 'Paused'}
                </span>
                <a href={`/employer/jobs/${job.id}/edit`} className="border border-gray-300 text-gray-600 px-3 py-1.5 rounded-lg text-sm hover:bg-gray-50">Edit</a>
                <a href={`/employer/jobs/${job.id}/applicants`} className="border border-indigo-300 text-indigo-600 px-3 py-1.5 rounded-lg text-sm hover:bg-indigo-50">Applicants</a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
