import React from 'react';

export default function ErrorView({ errorMsg, onTryAnother, onViewSupported }) {
  return (
    <div className="min-h-[calc(100vh-160px)] flex flex-col items-center justify-center p-unit-8 pt-20">
      <div className="w-full max-w-[600px] bg-surface-container rounded-xl border border-error/30 p-unit-8 shadow-2xl relative overflow-hidden flex flex-col items-center text-center">
        {/* Glowing Ambient Error Glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-64 bg-error/10 blur-3xl rounded-full pointer-events-none -z-10"></div>

        {/* Warning / Error Circle Icon */}
        <div className="w-16 h-16 rounded-full bg-error/10 border border-error/30 flex items-center justify-center text-error mb-unit-6 shadow-inner">
          <span className="material-symbols-outlined text-3xl">warning</span>
        </div>

        {/* Error Headline */}
        <h2 className="text-2xl font-bold text-on-surface mb-unit-3">
          Couldn't analyze this API
        </h2>

        {/* Error Details */}
        <p className="text-sm text-on-surface-variant max-w-md leading-relaxed mb-unit-6">
          {errorMsg || 'The provided documentation could not be parsed. Ensure the URL is public and follows OpenAPI 3.0+ specifications.'}
        </p>

        {/* Error Code Pill */}
        <div className="px-3 py-1 bg-surface-container-lowest border border-outline-variant/30 rounded font-mono text-xs text-error font-medium mb-unit-8">
          PARSE_ERR_OAS_VERSION_UNSUPPORTED
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center gap-unit-4 w-full justify-center">
          <button
            onClick={onTryAnother}
            className="w-full sm:w-auto px-unit-6 h-12 bg-primary text-on-primary font-mono text-xs uppercase tracking-wider font-bold rounded-lg hover:bg-primary-container transition-all shadow-md shadow-primary/20 flex items-center justify-center gap-2"
          >
            <span className="material-symbols-outlined text-sm">refresh</span>
            TRY ANOTHER URL
          </button>

          <button
            onClick={onViewSupported || onTryAnother}
            className="w-full sm:w-auto px-unit-6 h-12 bg-surface-container-high border border-outline-variant/30 text-on-surface hover:border-outline-variant transition-all font-mono text-xs uppercase tracking-wider font-bold rounded-lg flex items-center justify-center gap-2"
          >
            VIEW SUPPORTED FORMATS →
          </button>
        </div>
      </div>
    </div>
  );
}
