import React, { useState, useEffect } from 'react';

const LogExplorer = () => {
  const [logs, setLogs] = useState([
    { timestamp: '2026-04-02 21:40:12', level: 'INFO', message: 'Searching for anomalies in cluster-A...' },
    { timestamp: '2026-04-02 21:40:15', level: 'WARN', message: 'Latency spike detected in auth-service' },
    { type: 'insight', content: 'DETECTED: Unexpected latency spike in auth-service.' },
    { type: 'insight', content: 'ROOT CAUSE: DB connection pooling exhaustion (max_conn=100 reached).' },
    { type: 'insight', content: "SUGGESTED FIX: Increase 'pool_size' to 150 in config/database.yaml" }
  ]);

  return (
    <div className="mt-24 w-full max-w-5xl rounded-2xl border border-neutral-800 bg-neutral-900/50 backdrop-blur-xl p-4 shadow-2xl relative group opacity-0 animate-[fade-in_1s_ease-out_1.2s_forwards]">
      <div className="flex items-center gap-2 mb-4 px-2">
        <div className="w-3 h-3 rounded-full bg-neutral-800" />
        <div className="w-3 h-3 rounded-full bg-neutral-800" />
        <div className="w-3 h-3 rounded-full bg-neutral-800" />
        <div className="ml-4 text-xs text-neutral-600 font-mono tracking-wider">LOGARA_AI :: CLUSTER_EXPLORER</div>
      </div>
      <div className="aspect-[16/9] bg-neutral-950 rounded-xl overflow-hidden border border-neutral-800 flex flex-col p-8 relative">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(79,70,229,0.05)_0%,transparent_100%)] pointer-events-none" />
        <code className="text-indigo-400 font-mono text-sm leading-relaxed text-left flex-1">
          {logs.map((log, i) => (
            <div key={i} className="mb-1">
              {log.type === 'insight' ? (
                <div className="pl-4 border-l-2 border-indigo-900/50 text-neutral-300">
                  {log.content}
                </div>
              ) : (
                <>
                  <span className="text-neutral-500">[{log.timestamp}]</span>{' '}
                  <span className={log.level === 'INFO' ? 'text-emerald-400' : 'text-amber-400'}>{log.level}</span>: {log.message}
                </>
              )}
            </div>
          ))}
          <div className="mt-4"><span className="animate-pulse">_</span></div>
        </code>
      </div>
    </div>
  );
};

export default LogExplorer;
