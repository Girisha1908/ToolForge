import React from 'react';

export default function Header({ activeTab, onTabChange, currentState, onReset }) {
  return (
    <header className="fixed top-0 w-full z-50 bg-surface-container/80 backdrop-blur-xl shadow-[0_1px_8px_rgba(0,0,0,0.5)] border-b border-outline-variant/30">
      <div className="h-16 w-full px-unit-8 flex items-center justify-between">
        {/* Logo + Brand */}
        <div 
          className="flex items-center gap-unit-3 cursor-pointer"
          onClick={onReset}
        >
          <div className="w-8 h-8 rounded-lg bg-primary-container/20 border border-primary/40 flex items-center justify-center text-primary font-mono font-bold text-lg shadow-sm">
            TF
          </div>
          <span className="font-headline-lg text-2xl font-semibold tracking-tight text-on-surface">
            ToolForge
          </span>
        </div>

        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-unit-8">
          <button
            onClick={() => onTabChange('dashboard')}
            className={`font-mono text-xs uppercase tracking-widest transition-colors ${
              activeTab === 'dashboard'
                ? 'text-primary font-bold'
                : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => onTabChange('connectors')}
            className={`font-mono text-xs uppercase tracking-widest transition-colors ${
              activeTab === 'connectors'
                ? 'text-primary font-bold'
                : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            Connectors
          </button>
          <button
            onClick={() => onTabChange('documentation')}
            className={`font-mono text-xs uppercase tracking-widest transition-colors ${
              activeTab === 'documentation'
                ? 'text-primary font-bold'
                : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            Documentation
          </button>
        </nav>

        {/* Right side actions / user profile */}
        <div className="flex items-center gap-unit-6">
          <button 
            title="View API Specs / Code"
            className="p-unit-2 text-on-surface-variant hover:text-primary transition-colors flex items-center"
          >
            <span className="material-symbols-outlined text-xl">code</span>
          </button>

          <div className="flex items-center gap-unit-3 border-l border-outline-variant/30 pl-unit-6">
            <div className="text-right hidden sm:block">
              <p className="font-mono text-xs text-on-surface font-medium">Dev_Admin</p>
              <p className="text-[10px] text-on-surface-variant uppercase tracking-wider font-mono">
                PRO PLAN
              </p>
            </div>
            <div className="w-8 h-8 rounded-full bg-surface-container-high border border-outline-variant/50 flex items-center justify-center text-primary text-xs font-mono font-bold">
              DA
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
