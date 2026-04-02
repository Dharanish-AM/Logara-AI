import React from 'react';

const Navbar = () => {
  return (
    <nav className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-2 group cursor-pointer">
        <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center transform group-hover:rotate-12 transition-all duration-300 shadow-[0_0_20px_rgba(79,70,229,0.4)]">
          <span className="text-xl font-bold italic">L</span>
        </div>
        <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-neutral-400 bg-clip-text text-transparent">
          Logara AI
        </span>
      </div>
      <div className="hidden md:flex items-center gap-8 text-neutral-400 font-medium">
        <a href="#" className="hover:text-white transition-colors duration-200">Features</a>
        <a href="#" className="hover:text-white transition-colors duration-200">Architecture</a>
        <a href="#" className="hover:text-white transition-colors duration-200">Docs</a>
        <a href="https://github.com/Dharanish-AM/Logara-AI" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors duration-200">GitHub</a>
      </div>
      <button className="px-5 py-2 bg-white text-black font-semibold rounded-full hover:scale-105 active:scale-95 transition-all duration-200 shadow-xl shadow-white/5 cursor-pointer">
        Get Started
      </button>
    </nav>
  );
};

export default Navbar;
