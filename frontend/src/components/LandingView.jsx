import React, { useState } from 'react';

export default function LandingView({ onAnalyze }) {
  const [url, setUrl] = useState('');

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!url.trim()) return;
    onAnalyze(url.trim());
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
          Paste an API documentation URL. ToolForge analyzes the API, generates agent-ready tools, and provisions execution environments for your AI.
        </p>

        {/* Main Action Card */}
        <div className="w-full max-w-[800px] bg-surface-container/60 backdrop-blur-xl rounded-xl p-unit-6 md:p-unit-8 border border-outline-variant/20 shadow-xl relative overflow-hidden transition-all duration-300 hover:shadow-primary-container/10 hover:border-outline-variant/40 group">
          <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-primary/30 to-transparent"></div>
          
          <form onSubmit={handleSubmit} className="flex flex-col gap-unit-4">
            <label className="font-mono text-xs text-on-surface-variant uppercase tracking-widest text-left flex items-center justify-between">
              <span>API Documentation URL</span>
              <span className="text-[10px] text-outline flex items-center gap-1 opacity-80">
                <span className="material-symbols-outlined text-[14px]">bolt</span> OpenAPI 3.0+, Swagger 2.0, Postman
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
                disabled={!url.trim()}
                className="h-14 px-unit-8 bg-primary text-on-primary font-mono text-xs uppercase tracking-wider font-bold rounded-lg hover:bg-primary-container transition-all hover:-translate-y-0.5 active:translate-y-0 shadow-lg shadow-primary/20 whitespace-nowrap flex items-center justify-center gap-unit-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                ANALYZE API
                <span className="material-symbols-outlined text-sm">arrow_forward</span>
              </button>
            </div>

            <div className="flex items-center justify-between mt-unit-2">
              <div className="text-[12px] font-mono text-on-surface-variant/70">
                Supports public HTTP/HTTPS documentation endpoints
              </div>
            </div>
          </form>
        </div>
      </div>

      {/* Info Patterns Section */}
      <div className="w-full max-w-container-max mx-auto px-unit-8 py-unit-12 relative z-10 border-t border-outline-variant/10">
        <div className="mb-unit-8">
          <h2 className="text-xl font-bold text-on-surface flex items-center gap-unit-2">
            <span className="material-symbols-outlined text-outline">developer_board</span>
            Supported Input Formats
          </h2>
          <p className="text-sm text-on-surface-variant mt-unit-1">Provide any public API documentation URL to generate executable agent tools.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-unit-6">
          <div className="bg-surface-container-low border border-outline-variant/20 rounded-xl p-unit-6 flex flex-col">
            <div className="w-10 h-10 rounded-lg bg-surface flex items-center justify-center border border-outline-variant/20 mb-unit-4">
              <span className="material-symbols-outlined text-primary text-xl">description</span>
            </div>
            <h3 className="font-bold text-base text-on-surface mb-1">OpenAPI / Swagger</h3>
            <p className="text-xs text-on-surface-variant">Standard JSON or YAML specifications defining schemas, paths, and methods.</p>
          </div>

          <div className="bg-surface-container-low border border-outline-variant/20 rounded-xl p-unit-6 flex flex-col">
            <div className="w-10 h-10 rounded-lg bg-surface flex items-center justify-center border border-outline-variant/20 mb-unit-4">
              <span className="material-symbols-outlined text-secondary text-xl">view_module</span>
            </div>
            <h3 className="font-bold text-base text-on-surface mb-1">Postman Collections</h3>
            <p className="text-xs text-on-surface-variant">Postman v2/v2.1 collection endpoints with query parameters and request bodies.</p>
          </div>

          <div className="bg-surface-container-low border border-outline-variant/20 rounded-xl p-unit-6 flex flex-col">
            <div className="w-10 h-10 rounded-lg bg-surface flex items-center justify-center border border-outline-variant/20 mb-unit-4">
              <span className="material-symbols-outlined text-tertiary text-xl">article</span>
            </div>
            <h3 className="font-bold text-base text-on-surface mb-1">HTML / Text Documentation</h3>
            <p className="text-xs text-on-surface-variant">Structured or plain HTML documentation parsed through rule-based and LLM extraction.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
