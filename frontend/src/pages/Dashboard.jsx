import { useState, useEffect } from 'react';

function Dashboard() {
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8002';

  // State hooks
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    anomalies: 0,
    services: 0,
    aiStatus: 'checking',
    aiProgress: 0,
    aiModel: 'llama3'
  });

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResult, setSearchResult] = useState(null);
  const [isSearching, setIsSearching] = useState(false);

  // Log Ingestion state
  const [ingestText, setIngestText] = useState('');
  const [ingestService, setIngestService] = useState('default');
  const [isIngesting, setIsIngesting] = useState(false);
  const [ingestStatus, setIngestStatus] = useState(null);

  // Fetch dashboard stats & latest logs
  const fetchDashboardData = async () => {
    try {
      // 1. Fetch latest logs
      const logsRes = await fetch(`${API_URL}/logs?limit=50`);
      if (logsRes.ok) {
        const logsData = await logsRes.json();
        const logsList = logsData.logs || [];
        setLogs(logsList.slice(0, 8)); // Top 8 logs for display

        // Calculate stats
        const total = logsData.pagination?.total || logsList.length;
        const anomaliesCount = logsList.filter(log => 
          ['ERROR', 'CRITICAL', 'FATAL', 'WARN', 'WARNING'].includes(log.level.toUpperCase())
        ).length;
        
        const uniqueServices = new Set(logsList.map(log => 
          log.metadata?.service_id || log.metadata?.service || 'unknown_service'
        ));

        setStats(prev => ({
          ...prev,
          total,
          anomalies: anomaliesCount,
          services: uniqueServices.size
        }));
      }

      // 2. Fetch Ollama model manager status
      const aiRes = await fetch(`${API_URL}/api/ai/status`);
      if (aiRes.ok) {
        const aiData = await aiRes.json();
        setStats(prev => ({
          ...prev,
          aiStatus: aiData.status,
          aiProgress: aiData.progress,
          aiModel: aiData.model || prev.aiModel
        }));
      }
    } catch (err) {
      console.error("Failed to connect to backend api:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  // Handle Log Ingestion
  const handleIngest = async (e) => {
    e.preventDefault();
    if (!ingestText.trim()) return;

    setIsIngesting(true);
    setIngestStatus({ type: 'info', message: 'Sending log to ingestion pipeline...' });

    try {
      const res = await fetch(`${API_URL}/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          log_data: ingestText.trim(),
          service_id: ingestService.trim() || 'default'
        })
      });

      if (res.ok) {
        const data = await res.json();
        setIngestStatus({
          type: 'success',
          message: `Ingested successfully! Structuring output: "${data.structured_output?.['Problem Summary'] || 'Accepted'}"`
        });
        setIngestText('');
        // Refresh logs immediately
        fetchDashboardData();
      } else {
        const errData = await res.json();
        setIngestStatus({
          type: 'error',
          message: `Ingestion failed: ${errData.detail || 'Invalid payload'}`
        });
      }
    } catch (err) {
      setIngestStatus({
        type: 'error',
        message: `Network error: ${err.message}. Ensure backend is running.`
      });
    } finally {
      setIsIngesting(false);
    }
  };

  // Handle Semantic Search + AI generation
  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setSearchResult(null);

    try {
      const res = await fetch(`${API_URL}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery.trim(),
          limit: 5
        })
      });

      if (res.ok) {
        const data = await res.json();
        setSearchResult(data);
      } else {
        const errData = await res.json();
        console.error("Search failed:", errData);
      }
    } catch (err) {
      console.error("Search network error:", err);
    } finally {
      setIsSearching(false);
    }
  };

  // Helper for color-coding log levels
  const getLogLevelClass = (level) => {
    const lvl = level.toUpperCase();
    if (['ERROR', 'CRITICAL', 'FATAL'].includes(lvl)) {
      return 'border-rose-500/30 bg-rose-500/5 hover:border-rose-500/60 text-rose-200';
    }
    if (['WARN', 'WARNING'].includes(lvl)) {
      return 'border-amber-500/30 bg-amber-500/5 hover:border-amber-500/60 text-amber-200';
    }
    return 'border-indigo-500/10 bg-black/40 hover:border-indigo-500/40 text-neutral-200';
  };

  return (
    <div className="min-h-screen text-white py-12">
      {/* Header */}
      <div className="mb-12 fade-up flex justify-between items-end flex-wrap gap-4">
        <div>
          <h1 className="text-5xl font-black tracking-tight bg-gradient-to-r from-indigo-400 to-sky-400 bg-clip-text text-transparent">
            AI Observability Dashboard
          </h1>
          <p className="text-neutral-400 mt-4 max-w-2xl">
            Live log parsing, automated pattern clustering, and semantic search powered by Qdrant & Ollama.
          </p>
        </div>
        
        {/* Connection status badge */}
        <div className="flex items-center gap-2 px-4 py-2 rounded-full border border-emerald-500/20 bg-emerald-950/20 text-emerald-400 text-xs font-semibold">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          Connected to API:8002
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid md:grid-cols-4 gap-6 mb-12">
        <div className="ui-card group p-6 rounded-3xl border border-neutral-800 bg-neutral-950/80 backdrop-blur-xl hover:border-indigo-500/40 transition-all duration-300">
          <h2 className="text-neutral-400 text-sm">Logs Processed</h2>
          <p className="text-4xl font-black mt-3 transition-all duration-300 group-hover:text-indigo-300 group-hover:scale-105">
            {stats.total}
          </p>
          <div className="mt-5 h-[2px] w-0 bg-indigo-400 transition-all duration-500 group-hover:w-full" />
        </div>

        <div className="ui-card group p-6 rounded-3xl border border-neutral-800 bg-neutral-950/80 backdrop-blur-xl hover:border-rose-500/40 transition-all duration-300">
          <h2 className="text-neutral-400 text-sm">Anomalies Detected</h2>
          <p className="text-4xl font-rose-400 font-black mt-3 text-rose-400 transition-all duration-300 group-hover:scale-105">
            {stats.anomalies}
          </p>
          <div className="mt-5 h-[2px] w-0 bg-rose-400 transition-all duration-500 group-hover:w-full" />
        </div>

        <div className="ui-card group p-6 rounded-3xl border border-neutral-800 bg-neutral-950/80 backdrop-blur-xl hover:border-sky-500/40 transition-all duration-300">
          <h2 className="text-neutral-400 text-sm">Active Services</h2>
          <p className="text-4xl font-black mt-3 text-sky-400 transition-all duration-300 group-hover:translate-x-1">
            {stats.services}
          </p>
          <div className="mt-5 h-[2px] w-0 bg-sky-400 transition-all duration-500 group-hover:w-full" />
        </div>

        <div className="ui-card group p-6 rounded-3xl border border-neutral-800 bg-neutral-950/80 backdrop-blur-xl hover:border-emerald-500/40 transition-all duration-300">
          <h2 className="text-neutral-400 text-sm">LLM Status ({stats.aiModel})</h2>
          <div className="mt-3 flex flex-col">
            <span className={`text-xl font-bold uppercase ${stats.aiStatus === 'ready' ? 'text-emerald-400' : 'text-amber-400 animate-pulse'}`}>
              {stats.aiStatus}
            </span>
            {stats.aiStatus === 'pulling' && (
              <div className="w-full bg-neutral-800 rounded-full h-1.5 mt-2 overflow-hidden">
                <div 
                  className="bg-amber-400 h-1.5 rounded-full transition-all duration-500" 
                  style={{ width: `${stats.aiProgress}%` }}
                ></div>
              </div>
            )}
          </div>
          <div className="mt-5 h-[2px] w-0 bg-emerald-400 transition-all duration-500 group-hover:w-full" />
        </div>
      </div>

      {/* Main Sections Grid */}
      <div className="grid lg:grid-cols-3 gap-8">
        
        {/* Left/Middle Column (Ingestion & Search) */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* AI Semantic Search */}
          <div className="ui-card p-8 rounded-3xl border border-indigo-900/40 bg-neutral-950/80 backdrop-blur-xl hover:border-indigo-500/40 transition-all duration-300 hover:shadow-[0_0_40px_rgba(99,102,241,0.1)]">
            <h2 className="text-2xl font-bold text-indigo-400 mb-2">AI Semantic Search</h2>
            <p className="text-sm text-neutral-400 mb-6">
              Ask natural language questions about your logs. It embeds the query, finds matching vectors, and synthesizes answers.
            </p>

            <form onSubmit={handleSearch} className="flex gap-3 mb-6">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="e.g. Find database timeouts and sum their occurrences"
                className="flex-1 bg-black/50 border border-neutral-800 rounded-2xl px-5 py-3 text-white focus:outline-none focus:border-indigo-500/60 text-sm"
              />
              <button
                type="submit"
                disabled={isSearching || !searchQuery.trim()}
                className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:hover:bg-indigo-600 text-white font-semibold px-6 py-3 rounded-2xl transition-all text-sm shrink-0"
              >
                {isSearching ? 'Analyzing...' : 'Search'}
              </button>
            </form>

            {/* Search Result Output */}
            {searchResult && (
              <div className="space-y-6 pt-4 border-t border-neutral-900 animate-fade-in">
                {searchResult.answer && (
                  <div className="bg-indigo-950/30 border border-indigo-500/20 p-5 rounded-2xl">
                    <h3 className="text-sm font-bold text-indigo-300 mb-2">AI Summary Answer</h3>
                    <p className="text-sm text-neutral-300 leading-relaxed font-sans">{searchResult.answer}</p>
                  </div>
                )}
                
                <div>
                  <h3 className="text-sm font-bold text-neutral-400 mb-3">Matching Vectors</h3>
                  <div className="space-y-3">
                    {searchResult.logs && searchResult.logs.length > 0 ? (
                      searchResult.logs.map((log) => (
                        <div key={log.id} className="p-4 rounded-xl border border-neutral-900 bg-black/40 text-xs">
                          <div className="flex justify-between items-center mb-1">
                            <span className="font-semibold text-indigo-400">{log.metadata?.service_id || 'unknown'}</span>
                            <span className="text-neutral-500">{log.timestamp || 'No timestamp'}</span>
                          </div>
                          <p className="text-neutral-300 font-mono mt-1">{log.message}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-neutral-500 italic">No direct matches returned from vector database.</p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Log Ingest Simulator */}
          <div className="ui-card p-8 rounded-3xl border border-neutral-800 bg-neutral-950/80 backdrop-blur-xl">
            <h2 className="text-2xl font-bold mb-2">Ingest Log Entry</h2>
            <p className="text-sm text-neutral-400 mb-6">
              Simulate raw application logs. They will flow through the pipeline, undergo redaction, get queued to Redis, and index into Qdrant.
            </p>

            <form onSubmit={handleIngest} className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="col-span-2">
                  <label className="block text-xs font-semibold text-neutral-500 mb-2 uppercase">Log Data</label>
                  <input
                    type="text"
                    value={ingestText}
                    onChange={(e) => setIngestText(e.target.value)}
                    placeholder="e.g. ERROR: Database timeout for user 123"
                    className="w-full bg-black/50 border border-neutral-800 rounded-2xl px-5 py-3 text-white focus:outline-none focus:border-indigo-500/60 text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-neutral-500 mb-2 uppercase">Service ID</label>
                  <input
                    type="text"
                    value={ingestService}
                    onChange={(e) => setIngestService(e.target.value)}
                    placeholder="default"
                    className="w-full bg-black/50 border border-neutral-800 rounded-2xl px-5 py-3 text-white focus:outline-none focus:border-indigo-500/60 text-sm font-mono"
                  />
                </div>
              </div>

              <div className="flex justify-between items-center pt-2">
                {ingestStatus && (
                  <span className={`text-xs ${
                    ingestStatus.type === 'error' ? 'text-rose-400' : 
                    ingestStatus.type === 'success' ? 'text-emerald-400' : 'text-neutral-400'
                  }`}>
                    {ingestStatus.message}
                  </span>
                )}
                <div className="flex-1"></div>
                <button
                  type="submit"
                  disabled={isIngesting || !ingestText.trim()}
                  className="bg-neutral-800 hover:bg-neutral-700 disabled:opacity-50 text-white font-semibold px-6 py-2.5 rounded-2xl transition-all text-sm shrink-0 border border-neutral-700"
                >
                  {isIngesting ? 'Queuing...' : 'Queue Log'}
                </button>
              </div>
            </form>
          </div>

        </div>

        {/* Right Column (Live Logs Feed) */}
        <div>
          <div className="ui-card p-8 rounded-3xl border border-neutral-800 bg-neutral-950/80 backdrop-blur-xl h-full flex flex-col">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold">Recent Logs</h2>
              <button 
                onClick={fetchDashboardData}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold focus:outline-none"
              >
                Refresh
              </button>
            </div>

            <div className="space-y-4 flex-1 overflow-y-auto max-h-[500px] pr-2">
              {loading ? (
                <div className="text-center py-8 text-neutral-500 text-sm italic">Loading stream...</div>
              ) : logs.length > 0 ? (
                logs.map((log) => (
                  <div
                    key={log.id}
                    className={`
                      border
                      rounded-2xl
                      px-5
                      py-4
                      transition-all
                      duration-300
                      hover:translate-x-1
                      ${getLogLevelClass(log.level)}
                    `}
                  >
                    <div className="flex justify-between text-xs font-semibold text-neutral-400 mb-1">
                      <span>{log.metadata?.service_id || log.service_id || 'unknown'}</span>
                      <span className="uppercase text-[10px] bg-neutral-800 px-2 py-0.5 rounded text-neutral-300">
                        {log.level}
                      </span>
                    </div>
                    <p className="text-sm font-mono line-clamp-2 mt-1">{log.message}</p>
                    <div className="mt-2 flex justify-between items-center text-[10px] text-neutral-500">
                      <span>{log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'no time'}</span>
                      <span>{log.parser_type || 'raw'}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-12 text-neutral-500 text-sm italic border border-dashed border-neutral-800 rounded-2xl">
                  No logs ingested yet. Use the simulator below or curl to ingest logs.
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

export default Dashboard;