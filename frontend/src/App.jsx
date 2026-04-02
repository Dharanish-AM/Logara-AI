import React from 'react';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import LogExplorer from './components/LogExplorer';

function App() {
  return (
    <div className="min-h-screen bg-[#0c0a09] text-white selection:bg-indigo-500/30">
      <Navbar />

      <main className="max-w-7xl mx-auto px-8 pt-20 pb-32 relative overflow-hidden">
        {/* Decorative elements */}
        <div className="absolute top-0 -left-20 w-[500px] h-[500px] bg-indigo-600/10 blur-[120px] rounded-full -z-10 animate-pulse" />
        <div className="absolute bottom-0 -right-20 w-[500px] h-[500px] bg-sky-600/10 blur-[120px] rounded-full -z-10 animate-pulse delay-1000" />

        <div className="flex flex-col items-center text-center">
          <Hero />
          <LogExplorer />
        </div>
      </main>
    </div>
  );
}

export default App;
