import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-24 text-center">
      <h1 className="text-5xl font-bold text-gray-900 mb-6">Find Your Next Opportunity</h1>
      <p className="text-xl text-gray-500 mb-10">Browse hundreds of jobs at MOF Engineering and partner companies.</p>
      <div className="flex justify-center gap-4 flex-wrap">
        <Link to="/jobs" className="bg-indigo-600 text-white px-8 py-3 rounded-xl text-lg font-medium hover:bg-indigo-700">Browse Jobs</Link>
        <Link to="/register" className="border border-indigo-600 text-indigo-600 px-8 py-3 rounded-xl text-lg font-medium hover:bg-indigo-50">Create Account</Link>
      </div>
    </div>
  )
}
