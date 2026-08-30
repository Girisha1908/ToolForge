import React from 'react';

export default function ErrorView({ errorMsg, onTryAnother }) {
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
          Analysis Error
        </h2>

        {/* Error Details */}
        <p className="text-sm text-on-surface-variant max-w-md leading-relaxed mb-unit-8">
          {errorMsg || 'The provided documentation URL could not be processed. Please verify the URL and try again.'}
        </p>

        {/* Action Buttons */}
        <div className="flex items-center justify-center gap-unit-4 w-full">
          <button
            onClick={onTryAnother}
            className="px-unit-6 h-12 bg-primary text-on-primary font-mono text-xs uppercase tracking-wider font-bold rounded-lg hover:bg-primary-container transition-all shadow-md shadow-primary/20 flex items-center justify-center gap-2"
          >
            <span className="material-symbols-outlined text-sm">refresh</span>
            TRY ANOTHER URL
          </button>
        </div>
      </div>
    </div>
  );
}
