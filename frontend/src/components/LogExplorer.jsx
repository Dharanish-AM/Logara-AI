import { useEffect, useState } from 'react'

import { fetchLogs } from '../api'

const LogExplorer = () => {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let isMounted = true

    const loadLogs = async () => {
      try {
        const result = await fetchLogs()
        if (isMounted) {
          setLogs(result.logs || [])
          setLoading(false)
        }
      } catch {
        if (isMounted) {
          setError(true)
          setLoading(false)
        }
      }
    }

    loadLogs()

    return () => {
      isMounted = false
    }
  }, [])

  const getLevelClass = (level) => {
    if (level === 'ERROR') return 'text-red-400';
    if (level === 'WARN') return 'text-amber-400';
    if (level === 'INFO') return 'text-emerald-400';
    return 'text-neutral-400';
  };

  return (
    <div className="bg-neutral-950 rounded-3xl border border-neutral-800 p-8">
      <h2 className="text-2xl font-bold mb-6">Log Explorer</h2>
      <code className="block text-sm space-y-1 font-mono">
        {loading ? (
          <div className="text-neutral-500">Loading logs...</div>
        ) : error ? (
          <div className="text-red-400">Unable to load logs. Is the backend running?</div>
        ) : logs.length === 0 ? (
          <div className="text-neutral-500">No logs ingested yet.</div>
        ) : (
          logs.map((log, i) => (
            <div key={log.timestamp + i} className="mb-1">
              <span className="text-neutral-500">[{log.timestamp}]</span>{' '}
              <span className={getLevelClass(log.level)}>{log.level}</span>
              {': '}{log.message}{' '}
              <span className="text-neutral-500">({log.service})</span>
            </div>
          ))
        )}
        <div className="mt-4"><span className="animate-pulse">_</span></div>
      </code>
    </div>
  )
}

export default LogExplorer
