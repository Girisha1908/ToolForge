import React, { useState } from 'react';

export default function LandingView({ onAnalyze, onTriggerError }) {
  const [url, setUrl] = useState('https://petstore3.swagger.io/api/v3/openapi.json');

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!url.trim()) return;
    
    if (url.includes('error') || url.includes('invalid')) {
      onTriggerError(url);
    } else {
      onAnalyze(url);
    }
  };

  const handleSelectExample = (exampleUrl) => {
    setUrl(exampleUrl);
    onAnalyze(exampleUrl);
  };

  return (
    <div className="w-full flex flex-col items-center">
      {/* Hero / Main Section */}
      <div className="flex flex-col items-center justify-center pt-unit-12 pb-unit-8 px-unit-8 md:pt-[100px] md:pb-[60px] relative z-10 text-center w-full max-w-container-max">
        {/* Decorative Ambient Light */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[600px] bg-primary-container/10 blur-[120px] rounded-full pointer-events-none -z-10"></div>
        <div className="absolute top-[20%] right-[10%] w-[400px] h-[400px] bg-secondary-container/5 blur-[100px] rounded-full pointer-events-none -z-10"></div>

        {/* Status Pill */}
        <div className="inline-flex items-center gap-unit-2 px-unit-3 py-unit-1 rounded-full bg-surface-container-high border border-outline-variant/30 text-on-surface-variant text-[11px] uppercase tracking-widest font-mono mb-unit-6 shadow-sm">
          <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span>
          System Online
        </div>

        {/* Headline */}
        <h1 className="text-[36px] md:text-[54px] font-bold leading-[1.1] text-on-surface max-w-4xl tracking-tight mb-unit-6 bg-clip-text text-transparent bg-gradient-to-b from-on-surface via-on-surface to-on-surface-variant">
          Turn APIs into tools your <br className="hidden md:block"/> AI agents can actually use.
        </h1>

        {/* Description */}
        <p className="text-on-surface-variant max-w-2xl text-center text-base leading-relaxed mb-unit-12">
          Paste an API documentation URL. ToolForge analyzes the API, generates agent-ready tools, and provisions secure execution environments for your AI.
        </p>

        {/* Main Action Card */}
        <div className="w-full max-w-[800px] bg-surface-container/60 backdrop-blur-xl rounded-xl p-unit-6 md:p-unit-8 border border-outline-variant/20 shadow-xl relative overflow-hidden transition-all duration-300 hover:shadow-primary-container/10 hover:border-outline-variant/40 group">
          <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-primary/30 to-transparent"></div>
          
          <form onSubmit={handleSubmit} className="flex flex-col gap-unit-4">
            <label className="font-mono text-xs text-on-surface-variant uppercase tracking-widest text-left flex items-center justify-between">
              <span>API Documentation URL</span>
              <span className="text-[10px] text-outline flex items-center gap-1 opacity-80 transition-opacity">
                <span className="material-symbols-outlined text-[14px]">bolt</span> Auto-detects OpenAPI/Swagger
              </span>
            </label>

            <div className="relative flex flex-col md:flex-row gap-unit-3">
              <div className="relative flex-1">
                <span className="material-symbols-outlined absolute left-unit-4 top-1/2 -translate-y-1/2 text-on-surface-variant/50 text-lg">
                  link
                </span>
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://api.example.com/openapi.json"
                  className="w-full h-14 bg-surface-container-low border border-outline-variant/30 rounded-lg pl-unit-12 pr-unit-4 font-mono text-on-surface text-[15px] placeholder-on-surface-variant/30 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all shadow-inner"
                />
              </div>

              <button
                type="submit"
                className="h-14 px-unit-8 bg-primary text-on-primary font-mono text-xs uppercase tracking-wider font-bold rounded-lg hover:bg-primary-container transition-all hover:-translate-y-0.5 active:translate-y-0 shadow-lg shadow-primary/20 whitespace-nowrap flex items-center justify-center gap-unit-2"
              >
                ANALYZE API
                <span className="material-symbols-outlined text-sm">arrow_forward</span>
              </button>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between mt-unit-2 gap-2">
              <div className="text-[12px] font-mono text-on-surface-variant/70">
                Supports: OpenAPI 3.0+, Swagger 2.0, Postman Collections
              </div>
              <button
                type="button"
                onClick={() => handleSelectExample('https://petstore3.swagger.io/api/v3/openapi.json')}
                className="font-mono text-[12px] text-primary/80 hover:text-primary transition-colors flex items-center gap-1"
              >
                Try an example <span className="material-symbols-outlined text-[14px]">arrow_downward</span>
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Connectors / Examples Section */}
      <div className="w-full max-w-container-max mx-auto px-unit-8 py-unit-12 relative z-10 border-t border-outline-variant/10">
        <div className="flex flex-col md:flex-row items-start md:items-end justify-between mb-unit-8 gap-unit-4">
          <div>
            <h2 className="text-xl font-bold text-on-surface flex items-center gap-unit-2">
              <span className="material-symbols-outlined text-outline">developer_board</span>
              Connect your first API
            </h2>
            <p className="text-sm text-on-surface-variant mt-unit-1">Select an architecture pattern to see ToolForge in action.</p>
          </div>
          
          <div className="flex gap-2">
            <button 
              onClick={() => onTriggerError('https://invalid.example.com/v1/bad.json')}
              className="h-8 px-3 rounded bg-error/10 text-error border border-error/20 hover:bg-error/20 transition-colors flex items-center gap-1 font-mono text-[11px]"
            >
              <span className="material-symbols-outlined text-[14px]">bug_report</span> Test Error State
            </button>
          </div>
        </div>

        {/* Connector Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-unit-6">
          {/* GitHub Card */}
          <div 
            onClick={() => handleSelectExample('https://api.github.com/openapi')}
            className="group relative bg-surface-container-low border border-outline-variant/20 rounded-xl p-unit-6 hover:bg-surface-container transition-all duration-300 cursor-pointer overflow-hidden flex flex-col min-h-[200px]"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="w-12 h-12 rounded-lg bg-surface flex items-center justify-center border border-outline-variant/20 mb-unit-6 group-hover:border-primary/30 transition-colors shadow-sm">
              <svg className="w-6 h-6 fill-on-surface-variant group-hover:fill-primary transition-colors" viewBox="0 0 24 24">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
            </div>
            <h3 className="font-bold text-lg text-on-surface mb-unit-2 group-hover:text-primary transition-colors">GitHub</h3>
            <p className="text-xs text-on-surface-variant line-clamp-2 mb-auto">Repository management, issue tracking, and PR automation tools.</p>
            <div className="mt-unit-4 flex items-center justify-between text-xs text-outline">
              <span className="font-mono text-[10px] uppercase tracking-wider">12 Tools Available</span>
              <span className="material-symbols-outlined text-primary text-sm group-hover:translate-x-1 transition-transform">arrow_forward</span>
            </div>
          </div>

          {/* Twilio Card */}
          <div 
            onClick={() => handleSelectExample('https://api.twilio.com/swagger')}
            className="group relative bg-surface-container-low border border-outline-variant/20 rounded-xl p-unit-6 hover:bg-surface-container transition-all duration-300 cursor-pointer overflow-hidden flex flex-col min-h-[200px]"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="w-12 h-12 rounded-lg bg-surface flex items-center justify-center border border-outline-variant/20 mb-unit-6 group-hover:border-primary/30 transition-colors shadow-sm">
              <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary transition-colors text-2xl">
                forum
              </span>
            </div>
            <h3 className="font-bold text-lg text-on-surface mb-unit-2 group-hover:text-primary transition-colors">Twilio</h3>
            <p className="text-xs text-on-surface-variant line-clamp-2 mb-auto">Programmable messaging, voice, and communications APIs.</p>
            <div className="mt-unit-4 flex items-center justify-between text-xs text-outline">
              <span className="font-mono text-[10px] uppercase tracking-wider">8 Tools Available</span>
              <span className="material-symbols-outlined text-primary text-sm group-hover:translate-x-1 transition-transform">arrow_forward</span>
            </div>
          </div>

          {/* Jira Card */}
          <div 
            onClick={() => handleSelectExample('https://jira.atlassian.com/openapi')}
            className="group relative bg-surface-container-low border border-outline-variant/20 rounded-xl p-unit-6 hover:bg-surface-container transition-all duration-300 cursor-pointer overflow-hidden flex flex-col min-h-[200px]"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
            <div className="w-12 h-12 rounded-lg bg-surface flex items-center justify-center border border-outline-variant/20 mb-unit-6 group-hover:border-primary/30 transition-colors shadow-sm">
              <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary transition-colors text-2xl">
                task_alt
              </span>
            </div>
            <h3 className="font-bold text-lg text-on-surface mb-unit-2 group-hover:text-primary transition-colors">Jira</h3>
            <p className="text-xs text-on-surface-variant line-clamp-2 mb-auto">Issue tracking, sprint planning, and workflow automation endpoints.</p>
            <div className="mt-unit-4 flex items-center justify-between text-xs text-outline">
              <span className="font-mono text-[10px] uppercase tracking-wider">15 Tools Available</span>
              <span className="material-symbols-outlined text-primary text-sm group-hover:translate-x-1 transition-transform">arrow_forward</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
