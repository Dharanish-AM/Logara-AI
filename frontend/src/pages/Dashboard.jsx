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

    return () => { isMounted = false }
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

  const getLogHoverClass = (level) => {
    if (level === 'ERROR') return 'hover:border-rose-500/30 hover:bg-rose-500/5'
    if (level === 'WARN') return 'hover:border-amber-500/30 hover:bg-amber-500/5'
    return 'hover:border-emerald-500/30 hover:bg-emerald-500/5'
  }

  return (
    <div className="min-h-screen text-white py-12">

      {/* Header */}
      <div className="mb-12 fade-up">
        <h1 className="text-5xl font-black tracking-tight">
          AI Log Dashboard
        </h1>
        <p className="text-neutral-400 mt-4 max-w-2xl">
          Monitor anomalies, analyze logs, and discover infrastructure insights.
        </p>
      </div>

      {/* Stats */}
      <div className="grid md:grid-cols-4 gap-6 mb-16">

        <div className="ui-card group p-6 rounded-3xl border border-neutral-800 bg-neutral-950/80 backdrop-blur-xl hover:border-indigo-500/40">
          <h2 className="text-neutral-400 text-sm">Logs Processed</h2>
          <p className="text-4xl font-black mt-3 transition-all duration-300 group-hover:text-indigo-300 group-hover:scale-105">
            {data?.logs_processed ?? 0}
          </p>
          <div className="mt-5 h-[2px] w-0 bg-indigo-400 transition-all duration-500 group-hover:w-full" />
        </div>

        <div className="ui-card group p-6 rounded-3xl border border-neutral-800 bg-neutral-950/80 backdrop-blur-xl hover:border-rose-500/40">
          <h2 className="text-neutral-400 text-sm">Anomalies</h2>
          <p className="text-4xl font-black mt-3 text-rose-400 transition-all duration-300 group-hover:scale-110">
            {data?.anomalies ?? 0}
          </p>
          <div className="mt-5 h-[2px] w-0 bg-rose-400 transition-all duration-500 group-hover:w-full" />
        </div>

        <div className="ui-card group p-6 rounded-3xl border border-neutral-800 bg-neutral-950/80 backdrop-blur-xl hover:border-sky-500/40">
          <h2 className="text-neutral-400 text-sm">Active Services</h2>
          <p className="text-4xl font-black mt-3 text-sky-400 transition-all duration-300 group-hover:translate-x-1">
            {data?.active_services ?? 0}
          </p>
          <div className="mt-5 h-[2px] w-0 bg-sky-400 transition-all duration-500 group-hover:w-full" />
        </div>

        <div className="ui-card group p-6 rounded-3xl border border-neutral-800 bg-neutral-950/80 backdrop-blur-xl hover:border-emerald-500/40">
          <h2 className="text-neutral-400 text-sm">AI Insights</h2>
          <p className="text-4xl font-black mt-3 text-emerald-400 transition-all duration-300 group-hover:scale-110">
            {data?.ai_insights ?? 0}
          </p>
          <div className="mt-5 h-[2px] w-0 bg-emerald-400 transition-all duration-500 group-hover:w-full" />
        </div>

      </div>

      {/* AI Insight */}
      <div className="ui-card p-8 rounded-3xl border border-indigo-900/40 bg-neutral-950/80 backdrop-blur-xl mb-12 transition-all duration-300 hover:border-indigo-500/40 hover:shadow-[0_0_40px_rgba(99,102,241,0.15)]">
        <h2 className="text-2xl font-bold text-indigo-400 mb-4">
          AI Summary
        </h2>
        <p className="text-neutral-400 leading-8">
          {data?.ai_summary || 'No anomalies detected.'}
        </p>
      </div>

      {/* Recent Logs */}
      <div className="ui-card p-8 rounded-3xl border border-neutral-800 bg-neutral-950/80 backdrop-blur-xl">
        <h2 className="text-2xl font-bold mb-6">
          Recent Logs
        </h2>
        <div className="space-y-4">
          {recentLogs.length === 0 ? (
            <div className="bg-black/40 border border-white/5 rounded-2xl px-5 py-4">
              No recent logs available.
            </div>
          ) : (
            recentLogs.map((log, i) => (
              <div
                key={log.timestamp + i}
                className={`bg-black/40 border border-white/5 rounded-2xl px-5 py-4 transition-all duration-300 hover:translate-x-1 ${getLogHoverClass(log.level)}`}
              >
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