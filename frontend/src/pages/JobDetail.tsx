import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../lib/api'

interface Job {
  id: number
  title: string
  type: string
  location: string | null
  is_remote: boolean
  description: string | null
  requirements: string | null
  benefits: string | null
  skills_required: string | null
  salary_min: number | null
  salary_max: number | null
  experience_level: string | null
  department: string | null
  company_name: string | null
  created_at: string
  applied: boolean
  saved: boolean
}

export default function JobDetail() {
  const { id } = useParams<{ id: string }>()
  const [job, setJob] = useState<Job | null>(null)
  const [loading, setLoading] = useState(true)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api.get<Job>(`/jobs/${id}`)
      .then((r) => { setJob(r.data); setSaved(r.data.saved) })
      .finally(() => setLoading(false))
  }, [id])

  const toggleSave = async () => {
    await api.post(`/jobs/${id}/save`)
    setSaved((s) => !s)
  }

  if (loading) return <div className="text-center py-20 text-gray-400">Loading…</div>
  if (!job) return <div className="text-center py-20 text-gray-400">Job not found.</div>

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Link to="/jobs" className="text-indigo-600 text-sm mb-6 inline-block">← Back to Jobs</Link>
      <div className="bg-white border border-gray-200 rounded-2xl p-8">
        <div className="flex items-start justify-between gap-4 flex-wrap mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">{job.title}</h1>
            <div className="text-sm text-gray-500 flex gap-3 flex-wrap">
              {job.company_name && <span className="font-medium text-indigo-600">{job.company_name}</span>}
              {job.location && <span>📍 {job.location}</span>}
              <span>{job.type}</span>
              {job.is_remote && <span className="text-purple-600">Remote</span>}
              {job.experience_level && <span>{job.experience_level}</span>}
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={toggleSave}
              className={`border px-4 py-2 rounded-lg text-sm ${saved ? 'border-indigo-600 bg-indigo-50 text-indigo-600' : 'border-gray-300 text-gray-600'}`}>
              {saved ? '🔖 Saved' : '🔖 Save'}
            </button>
            {!job.applied ? (
              <a href={`/user/apply/${job.id}`}
                className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm hover:bg-indigo-700">Apply Now</a>
            ) : (
              <span className="bg-green-100 text-green-700 px-5 py-2 rounded-lg text-sm font-medium">✓ Applied</span>
            )}
          </div>
        </div>

        {job.description && (
          <section className="mb-6">
            <h2 className="text-base font-semibold mb-2">Description</h2>
            <p className="text-sm text-gray-600 whitespace-pre-wrap leading-relaxed">{job.description}</p>
          </section>
        )}
        {job.requirements && (
          <section className="mb-6">
            <h2 className="text-base font-semibold mb-2">Requirements</h2>
            <p className="text-sm text-gray-600 whitespace-pre-wrap leading-relaxed">{job.requirements}</p>
          </section>
        )}
        {job.skills_required && (
          <section className="mb-6">
            <h2 className="text-base font-semibold mb-2">Skills</h2>
            <div className="flex flex-wrap gap-2">
              {job.skills_required.split(',').filter(Boolean).map((s) => (
                <span key={s} className="bg-gray-100 border border-gray-200 px-3 py-1 rounded-full text-xs">{s.trim()}</span>
              ))}
            </div>
          </section>
        )}
        {job.benefits && (
          <section>
            <h2 className="text-base font-semibold mb-2">Benefits</h2>
            <p className="text-sm text-gray-600 whitespace-pre-wrap leading-relaxed">{job.benefits}</p>
          </section>
        )}
      </div>
    </div>
  )
}
