import React, { useState } from 'react';

function Dashboard() {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [stats, setStats] = useState({
    logsProcessed: '24.5K',
    anomalies: 12,
    activeServices: 8,
    aiInsights: 34
  });

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      setStats({
        logsProcessed: `${(24.5 + Math.random() * 0.2).toFixed(1)}K`,
        anomalies: Math.floor(12 + Math.random() * 3),
        activeServices: 8,
        aiInsights: Math.floor(34 + Math.random() * 2)
      });
      setIsRefreshing(false);
    }, 600);
  };

  const handleExport = () => {
    const summaryText = `LOGARA AI DASHBOARD REPORT\n====================\n\nAI Summary:\nElevated database timeout errors detected after deployment v2.1. Similar patterns occurred 3 days ago and correlate with Redis latency spikes.\n\nMetrics:\n- Logs Processed: ${stats.logsProcessed}\n- Anomalies: ${stats.anomalies}\n- Active Services: ${stats.activeServices}\n- AI Insights: ${stats.aiInsights}`;
    const blob = new Blob([summaryText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'logara-ai-summary.txt';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

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
        <button 
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="mt-6 flex items-center gap-2 px-4 py-2 bg-neutral-900 border border-neutral-800 hover:border-neutral-600 rounded-xl text-xs font-semibold transition-all active:scale-95 disabled:opacity-50"
        >
          <span className={`w-2 h-2 rounded-full bg-indigo-500 ${isRefreshing ? 'animate-ping' : ''}`} />
          {isRefreshing ? 'Refreshing Stream...' : 'Refresh Stream'}
        </button>
      </div>

{/* Stats */}
      <div className="grid md:grid-cols-4 gap-6 mb-16">

        <div className="bg-neutral-950 p-6 rounded-3xl border border-neutral-800 hover:-translate-y-1 transition-all duration-300 shadow-lg shadow-black/50">
          <h2 className="text-neutral-400">Logs Processed</h2>
          <p className="text-3xl font-bold mt-2">{stats.logsProcessed}</p>
        </div>

        <div className="bg-neutral-950 p-6 rounded-3xl border border-neutral-800 hover:-translate-y-1 transition-all duration-300 shadow-lg shadow-black/50">
          <h2 className="text-neutral-400">Anomalies</h2>
          <p className="text-3xl font-bold mt-2 text-red-400">{stats.anomalies}</p>
        </div>

        <div className="bg-neutral-950 p-6 rounded-3xl border border-neutral-800 hover:-translate-y-1 transition-all duration-300 shadow-lg shadow-black/50">
          <h2 className="text-neutral-400">Active Services</h2>
          <p className="text-3xl font-bold mt-2 text-sky-400">{stats.activeServices}</p>
        </div>

        <div className="bg-neutral-950 p-6 rounded-3xl border border-neutral-800 hover:-translate-y-1 transition-all duration-300 shadow-lg shadow-black/50">
          <h2 className="text-neutral-400">AI Insights</h2>
          <p className="text-3xl font-bold mt-2 text-emerald-400">{stats.aiInsights}</p>
        </div>

      </div>
     
      {/* AI Insight */}
      <div className="bg-neutral-950 p-8 rounded-3xl border border-indigo-900 mb-12 clear-both overflow-hidden">

        <button 
          onClick={handleExport}
          className="float-right text-xs bg-neutral-900 border border-neutral-800 hover:border-indigo-800 px-3 py-1.5 rounded-xl font-medium transition-all text-indigo-400 active:scale-95"
        >
          Export Report (.txt)
        </button>

        <h2 className="text-2xl font-bold text-indigo-400 mb-4">
          AI Summary
        </h2>

        <p className="text-neutral-400">
          Elevated database timeout errors detected after deployment v2.1.
          Similar patterns occurred 3 days ago and correlate with Redis latency spikes.
        </p>

      </div>
      {/* Interactive Log Ingestion Action Panel */}
      <div className="bg-neutral-950 p-8 rounded-3xl border border-neutral-800 mb-12 shadow-xl">
        <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          Test Log Ingestion Engine
        </h2>
        <p className="text-sm text-neutral-400 mb-6">
          Simulate streaming data payload injection directly into the microservice architecture stack.
        </p>

        <form onSubmit={(e) => {
          e.preventDefault();
          const form = e.target;
          const logInput = form.elements.logMessage.value;
          if (!logInput.trim()) return;

          // Visual feedback for simulated ingestion
          const submitBtn = form.querySelector('button[type="submit"]');
          const originalText = submitBtn.innerHTML;
          submitBtn.disabled = true;
          submitBtn.innerHTML = 'Ingesting Payload...';

          setTimeout(() => {
            // Dynamically update the logs counter to show it worked!
            setStats(prev => ({
              ...prev,
              logsProcessed: `${(parseFloat(prev.logsProcessed) + 0.1).toFixed(1)}K`
            }));
            
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Success ✓';
            form.reset();

            setTimeout(() => {
              submitBtn.innerHTML = originalText;
            }, 1500);
          }, 700);
        }} className="flex flex-col sm:flex-row gap-4">
          <input
            name="logMessage"
            type="text"
            placeholder="e.g., CRITICAL: Auth token validation failed for user_id_9082..."
            className="flex-1 bg-black border border-neutral-800 rounded-2xl px-4 py-3 text-sm text-neutral-300 focus:outline-none focus:border-neutral-600 transition-colors font-mono"
            required
          />
          <button
            type="submit"
            className="px-6 py-3 bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white font-semibold text-sm rounded-2xl transition-all shadow-lg shadow-emerald-950/20 whitespace-nowrap disabled:opacity-50"
          >
            Stream Single Log
          </button>
        </form>
      </div>


      {/* Recent Logs */}
      <div className="bg-neutral-950 p-8 rounded-3xl border border-neutral-800">

        <h2 className="text-2xl font-bold mb-6">
          Recent Logs
        </h2>

        <div className="space-y-4">

          <div className="p-4 rounded-xl bg-black">
            ERROR: Database timeout detected
          </div>

          <div className="p-4 rounded-xl bg-black">
            WARNING: Redis queue delay increased
          </div>

          <div className="p-4 rounded-xl bg-black">
            INFO: Service health restored
          </div>

        </div>

      </div>

    </div>
  );
}

export default Dashboard;