import { useEffect, useState, useCallback } from 'react'
import { fetchLogs } from '../api'

const LogExplorer = () => {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [retryCount, setRetryCount] = useState(0)

  const loadLogs = useCallback(async (showLoading = true) => {
    if (showLoading) {
      setLoading(true)
      setError(false)
    }
    try {
      const result = await fetchLogs()
      setLogs(result.logs || [])
      setError(false)
      setLoading(false)
    } catch {
      setError(true)
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let isMounted = true
    if (isMounted) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      loadLogs(true)
    }
    return () => {
      isMounted = false
    }
  }, [loadLogs])

  // Auto-retry effect when backend is starting up
  useEffect(() => {
    if (!error || retryCount >= 5) return

    const timer = setTimeout(() => {
      setRetryCount(prev => prev + 1)
      loadLogs(false) // retry silently without flashing loader
    }, 3000)

    return () => clearTimeout(timer)
  }, [error, retryCount, loadLogs])

  const getLevelClass = (level) => {
    if (level === 'ERROR') return 'text-red-400';
    if (level === 'WARN') return 'text-amber-400';
    if (level === 'INFO') return 'text-emerald-400';
    return 'text-neutral-400';
  };

  return (
    <div className="bg-neutral-950 rounded-3xl border border-neutral-800 p-8">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-cyan-400">Log Explorer</h2>
        {!loading && !error && (
          <span className="text-sm text-neutral-500">
            {logs.length} logs loaded
          </span>
        )}
      </div>
      <code className="block text-sm space-y-1 font-mono">
        {loading ? (
          <div>
            <div className="flex justify-between items-center mb-4">
              <span className="text-sm text-neutral-400 animate-pulse">
                Fetching latest log entries...
              </span>
              <span className="animate-spin text-neutral-500">⟳</span>
            </div>
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center gap-3 animate-pulse">
                  <div className="h-3 w-24 bg-neutral-800 rounded"></div>
                  <div className="h-3 w-16 bg-red-900/40 rounded"></div>
                  <div className="h-3 flex-1 bg-neutral-800 rounded"></div>
                  <div className="h-3 w-20 bg-neutral-800 rounded"></div>
                </div>
              ))}
            </div>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <div className="text-red-400 mb-4 font-semibold flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
              Unable to connect to the backend API. Is the backend running?
            </div>
            <button
              onClick={() => {
                setRetryCount(0);
                loadLogs(true);
              }}
              className="px-4 py-2 bg-neutral-900 hover:bg-neutral-850 border border-neutral-800 text-neutral-200 text-sm font-medium rounded-xl transition duration-200 shadow-sm flex items-center gap-2 cursor-pointer"
            >
              <span>⟳</span> Retry Connection
            </button>
          </div>
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
