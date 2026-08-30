import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';

export default function AnalysisView({ url, onComplete, onError, onCancel }) {
  const [stage, setStage] = useState('FETCHING'); // FETCHING | PROCESSING | FINALIZING
  const targetHost = url ? url.replace(/^https?:\/\//, '').toUpperCase() : 'API DOCUMENTATION';

  useEffect(() => {
    let isMounted = true;

    async function processDoc() {
      try {
        if (isMounted) setStage('FETCHING');
        
        // Timer to reflect backend pipeline phases honestly
        const stageTimer = setTimeout(() => {
          if (isMounted) setStage('PROCESSING');
        }, 800);

        const connector = await apiService.generateTools(url);
        clearTimeout(stageTimer);

        if (isMounted) {
          setStage('FINALIZING');
          setTimeout(() => {
            if (isMounted) onComplete(connector);
          }, 300);
        }
      } catch (err) {
        if (isMounted) {
          onError(err.message || 'Failed to process API documentation.');
        }
      }
    }

    processDoc();

    return () => {
      isMounted = false;
    };
  }, [url, onComplete, onError]);

  return (
    <div className="max-w-container-max mx-auto px-unit-8 w-full py-unit-8 flex flex-col gap-unit-8 pt-20">
      {/* Sub-Header */}
      <div className="flex items-end justify-between border-b border-outline-variant/30 pb-unit-4">
        <div>
          <h1 className="text-2xl font-bold text-on-surface">Analysis Workspace</h1>
          <p className="text-sm text-on-surface-variant mt-unit-1">Parsing API documentation and generating tool definitions.</p>
        </div>
        <div className="flex items-center gap-unit-2">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-secondary"></span>
          </span>
          <span className="font-mono text-xs text-secondary uppercase tracking-widest font-bold">Processing</span>
        </div>
      </div>

      {/* Main Analysis Card */}
      <div className="bg-surface-container rounded-xl shadow-lg border border-outline-variant/30 overflow-hidden relative p-unit-8">
        <div className="flex justify-between items-center pb-unit-6 border-b border-outline-variant/30">
          <div className="flex items-center gap-unit-3">
            <span className="material-symbols-outlined text-primary text-[28px] animate-pulse">radar</span>
            <div>
              <h2 className="text-lg font-bold text-on-surface">Analyzing Documentation</h2>
              <p className="font-mono text-xs text-on-surface-variant uppercase tracking-widest mt-1">
                TARGET: {targetHost}
              </p>
            </div>
          </div>
          <button
            onClick={onCancel}
            className="font-mono text-xs text-on-surface-variant hover:text-error transition-colors uppercase tracking-widest px-unit-4 py-unit-2 rounded bg-surface border border-outline-variant/30 hover:border-error/50"
          >
            Cancel
          </button>
        </div>

        <div className="py-unit-8 flex flex-col items-center justify-center text-center">
          <span className="material-symbols-outlined text-primary text-5xl animate-spin mb-4">
            progress_activity
          </span>
          <h3 className="text-lg font-bold text-on-surface mb-2">
            {stage === 'FETCHING' && 'Fetching Documentation...'}
            {stage === 'PROCESSING' && 'Ingesting Schemas & Generating Tools...'}
            {stage === 'FINALIZING' && 'Registering Tools in Workspace...'}
          </h3>
          <p className="text-sm text-on-surface-variant max-w-md">
            Ingesting endpoints, parameters, authentication requirements, and generating validated tool definitions via ToolForge engine.
          </p>
        </div>
      </div>
    </div>
  );
}
