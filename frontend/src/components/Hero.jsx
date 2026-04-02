import React from 'react';

const Hero = () => {
  return (
    <div className="flex flex-col items-center text-center">
      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-sm font-medium mb-8 animate-fade-in">
        <span className="flex h-2 w-2 rounded-full bg-indigo-400" />
        Now in Public Beta
      </div>
      
      <h1 className="text-6xl md:text-8xl font-black tracking-tight mb-8 leading-[1.1] animate-title">
        Log Intelligence. 
        <span className="block bg-gradient-to-r from-indigo-400 via-sky-400 to-emerald-400 bg-[length:200%_auto] bg-clip-text text-transparent animate-gradient">
          Powered by AI.
        </span>
      </h1>

      <p className="max-w-2xl text-lg md:text-xl text-neutral-400 mb-12 leading-relaxed opacity-0 animate-[fade-in_1s_ease-out_0.5s_forwards]">
        Detect anomalies, summarize issues, and perform root cause analysis with actionable fixes.
        Logara AI turns your raw logs into searchable, high-value intelligence.
      </p>

      <div className="flex flex-col sm:flex-row gap-4 opacity-0 animate-[fade-in_1s_ease-out_0.8s_forwards]">
        <button className="px-8 py-4 bg-indigo-600 text-white font-bold rounded-2xl hover:bg-indigo-500 transition-all duration-300 shadow-lg shadow-indigo-600/25 group cursor-pointer">
          Deploy Locally
          <span className="inline-block ml-2 group-hover:translate-x-1 transition-transform">→</span>
        </button>
        <button className="px-8 py-4 bg-neutral-900 text-white font-bold rounded-2xl border border-neutral-800 hover:bg-neutral-800 transition-all duration-300 cursor-pointer">
          Read the Docs
        </button>
      </div>
    </div>
  );
};

export default Hero;
