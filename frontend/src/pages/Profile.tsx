import { useEffect, useState } from 'react'
import api from '../lib/api'

interface Profile {
  full_name: string
  email: string
  headline: string | null
  location_city: string | null
  skills: string | null
  resume_headline: string | null
}

export default function Profile() {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api.get<Profile>('/profile').then((r) => setProfile(r.data))
  }, [])

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setSaving(true)
    const fd = new FormData(e.currentTarget)
    await api.patch('/profile', Object.fromEntries(fd))
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
    setSaving(false)
  }

  if (!profile) return <div className="text-center py-20 text-gray-400">Loading…</div>

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">My Profile</h1>
      <div className="bg-white border border-gray-200 rounded-2xl p-8">
        {saved && <div className="bg-green-50 text-green-600 text-sm p-3 rounded-lg mb-5">Saved!</div>}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
            <input name="full_name" defaultValue={profile.full_name}
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Headline</label>
            <input name="headline" defaultValue={profile.headline || ''}
              placeholder="e.g. Senior Software Engineer"
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Location</label>
            <input name="location_city" defaultValue={profile.location_city || ''}
              placeholder="City, Country"
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Skills (comma-separated)</label>
            <input name="skills" defaultValue={profile.skills || ''}
              placeholder="Python, Flask, SQL…"
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Summary</label>
            <textarea name="resume_headline" defaultValue={profile.resume_headline || ''} rows={3}
              placeholder="Brief professional summary…"
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <button type="submit" disabled={saving}
            className="bg-indigo-600 text-white py-2.5 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-60">
            {saving ? 'Saving…' : 'Save Profile'}
          </button>
        </form>
      </div>
    </div>
  )
}
