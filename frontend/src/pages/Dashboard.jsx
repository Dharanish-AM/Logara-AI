import { useEffect, useState } from 'react'

import { fetchDashboard } from '../api'

function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let isMounted = true

    const loadDashboard = async () => {
      try {
        const result = await fetchDashboard()
        if (isMounted) {
          setData(result)
          setLoading(false)
        }
      } catch {
        if (isMounted) {
          setError(true)
          setLoading(false)
        }
      }
    }

    loadDashboard()

    return () => {
      isMounted = false
    }
  }, [])

  if (loading) {
    return <div className="min-h-screen text-white py-12">Loading dashboard...</div>
  }

  if (error) {
    return <div className="min-h-screen text-white py-12">Unable to reach backend. Is the server running?</div>
  }

  const recentLogs = data?.recent_logs || []

  const getLevelClass = (level) => {
    if (level === 'ERROR') return 'text-red-400'
    if (level === 'WARN') return 'text-amber-400'
    if (level === 'INFO') return 'text-emerald-400'
    return 'text-neutral-400'
  }

  return (
    <div className="min-h-screen text-white py-12">

      {/* Header */}
      <div className="mb-12">
        <h1 className="text-5xl font-black">
          AI Log Dashboard
        </h1>

        <p className="text-neutral-400 mt-4">
          Monitor anomalies, analyze logs, and discover infrastructure insights.
        </p>
      </div>

      {/* Stats */}
      <div className="grid md:grid-cols-4 gap-6 mb-16">

        <div className="bg-neutral-950 p-6 rounded-3xl border border-neutral-800">
          <h2 className="text-neutral-400">Logs Processed</h2>
          <p className="text-3xl font-bold mt-2">{data?.logs_processed ?? 0}</p>
        </div>

        <div className="bg-neutral-950 p-6 rounded-3xl border border-neutral-800">
          <h2 className="text-neutral-400">Anomalies</h2>
          <p className="text-3xl font-bold mt-2 text-red-400">{data?.anomalies ?? 0}</p>
        </div>

        <div className="bg-neutral-950 p-6 rounded-3xl border border-neutral-800">
          <h2 className="text-neutral-400">Active Services</h2>
          <p className="text-3xl font-bold mt-2 text-sky-400">{data?.active_services ?? 0}</p>
        </div>

        <div className="bg-neutral-950 p-6 rounded-3xl border border-neutral-800">
          <h2 className="text-neutral-400">AI Insights</h2>
          <p className="text-3xl font-bold mt-2 text-emerald-400">{data?.ai_insights ?? 0}</p>
        </div>

      </div>


      {/* AI Insight */}
      <div className="bg-neutral-950 p-8 rounded-3xl border border-indigo-900 mb-12">

        <h2 className="text-2xl font-bold text-indigo-400 mb-4">
          AI Summary
        </h2>

        <p className="text-neutral-400">
          {data?.ai_summary || 'No anomalies detected.'}
        </p>

      </div>


      {/* Recent Logs */}
      <div className="bg-neutral-950 p-8 rounded-3xl border border-neutral-800">

        <h2 className="text-2xl font-bold mb-6">
          Recent Logs
        </h2>

        <div className="space-y-4">
          {recentLogs.length === 0 ? (
            <div className="p-4 rounded-xl bg-black">No recent logs available.</div>
          ) : (
            recentLogs.map((log, i) => (
              <div key={log.timestamp + i} className="p-4 rounded-xl bg-black">
                <span className="text-neutral-500">[{log.timestamp}]</span>{' '}
                <span className={getLevelClass(log.level)}>{log.level}</span>
                {': '}{log.message}
              </div>
            ))
          )}
        </div>

      </div>

    </div>
  )
}

export default Dashboard
