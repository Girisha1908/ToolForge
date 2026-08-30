import React, { useEffect, useState } from 'react';
import { parseApi } from '../services/apiService';

export default function AnalysisView({ url, onComplete, onTriggerError, onCancel }) {
  const [percent, setPercent] = useState(0);
  const [toolsCount, setToolsCount] = useState(0);
  const [errorOccurred, setErrorOccurred] = useState(false);

  useEffect(() => {
    let parsedData = null;
    let isMounted = true;

    // Trigger the real parsing process on the backend
    parseApi(url)
      .then((data) => {
        if (isMounted) {
          parsedData = data;
          setToolsCount(data.tools?.length || 0);
        }
      })
      .catch((err) => {
        console.error(err);
        if (isMounted) {
          setErrorOccurred(true);
          if (onTriggerError) {
            onTriggerError(url, `API Analysis failed: ${err.message}`);
          }
        }
      });

    // Run progress bar animation
    const timer = setInterval(() => {
      if (errorOccurred) {
        clearInterval(timer);
        return;
      }
      setPercent((prev) => {
        if (prev >= 100) {
          clearInterval(timer);
          // Wait until the real backend parse request resolves
          const checkInterval = setInterval(() => {
            if (parsedData) {
              clearInterval(checkInterval);
              onComplete(parsedData);
            }
          }, 100);
          return 100;
        }
        return prev + 5;
      });
    }, 150);

    return () => {
      isMounted = false;
      clearInterval(timer);
    };
  }, [url, errorOccurred, onComplete, onTriggerError]);

  const targetHost = url ? url.replace(/^https?:\/\//, '').split('/')[0].toUpperCase() : 'API.EXAMPLE.COM';

  const getStepState = (stepIndex) => {
    const thresholds = [0, 15, 35, 55, 75, 90];
    const threshold = thresholds[stepIndex];
    const nextThreshold = stepIndex < 5 ? thresholds[stepIndex + 1] : 101;

    if (percent >= nextThreshold) return 'done';
    if (percent >= threshold && percent < nextThreshold) return 'active';
    return 'pending';
  };

  const renderStep = (index, title, activeSubtitle, doneSubtitle) => {
    const state = getStepState(index);
    if (state === 'done') {
      return (
        <div key={index} className="flex items-start gap-unit-4 opacity-80 transition-opacity">
          <div className="mt-1 flex-shrink-0">
            <div className="w-6 h-6 rounded-full bg-secondary/20 flex items-center justify-center border border-secondary/50">
              <span className="material-symbols-outlined text-secondary text-[16px]">check</span>
            </div>
          </div>
          <div className="flex-1">
            <h3 className="text-base font-medium text-on-surface">{title}</h3>
            <p className="font-mono text-xs text-secondary uppercase tracking-widest mt-0.5">{doneSubtitle}</p>
          </div>
        </div>
      );
    }
    if (state === 'active') {
      return (
        <div key={index} className="flex items-start gap-unit-4 relative group">
          <div className="mt-1 flex-shrink-0 relative">
            <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center border border-primary relative z-10">
              <span className="material-symbols-outlined text-primary text-[14px] animate-spin">refresh</span>
            </div>
            <div className="absolute inset-0 rounded-full border border-primary animate-ping opacity-50 z-0"></div>
          </div>
          <div className="flex-1 bg-surface rounded-lg p-unit-4 border-l-2 border-primary -mt-unit-2 shadow-md">
            <h3 className="text-base font-bold text-primary">{title}</h3>
            <div className="flex items-center gap-unit-2 mt-2">
              <div className="w-full bg-surface-variant rounded-full h-1.5 overflow-hidden">
                <div 
                  className="bg-primary h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${percent}%` }}
                ></div>
              </div>
              <span className="font-mono text-xs text-on-surface-variant min-w-[40px] text-right">{percent}%</span>
            </div>
            <p className="text-xs text-on-surface-variant mt-2">{activeSubtitle}</p>
          </div>
        </div>
      );
    }
    return (
      <div key={index} className="flex items-start gap-unit-4 opacity-40">
        <div className="mt-1 flex-shrink-0">
          <div className="w-6 h-6 rounded-full bg-surface-variant flex items-center justify-center border border-outline-variant/50">
            <div className="w-2 h-2 rounded-full bg-outline-variant"></div>
          </div>
        </div>
        <div className="flex-1">
          <h3 className="text-base font-medium text-on-surface-variant">{title}</h3>
          <p className="font-mono text-xs text-outline uppercase tracking-widest mt-0.5">Pending</p>
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-container-max mx-auto px-unit-8 w-full py-unit-8 flex flex-col gap-unit-8 pt-20">
      {/* Sub-Header */}
      <div className="flex items-end justify-between border-b border-outline-variant/30 pb-unit-4">
        <div>
          <h1 className="text-2xl font-bold text-on-surface">Dashboard</h1>
          <p className="text-sm text-on-surface-variant mt-unit-1">Connect, monitor, and manage your agent tooling.</p>
        </div>
        <div className="flex items-center gap-unit-2">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-secondary"></span>
          </span>
          <span className="font-mono text-xs text-secondary uppercase tracking-widest font-bold">System Operational</span>
        </div>
      </div>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-unit-6">
        {/* Left Column: Analysis Progress Card */}
        <div className="lg:col-span-8 flex flex-col gap-unit-6">
          <div className="bg-surface-container rounded-xl shadow-lg border border-outline-variant/30 overflow-hidden relative">
            <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none"></div>
            
            <div className="p-unit-6 border-b border-outline-variant/30 flex justify-between items-center relative z-10">
              <div className="flex items-center gap-unit-3">
                <span className="material-symbols-outlined text-primary text-[28px] animate-pulse">radar</span>
                <div>
                  <h2 className="text-lg font-bold text-on-surface">Analyzing API</h2>
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

            <div className="p-unit-8 relative z-10">
              {/* Progress Checklist */}
              <div className="flex flex-col gap-unit-6">
                {renderStep(0, "Fetching API specification", "Connecting to documentation source...", "Connection Established")}
                {renderStep(1, "Detecting authentication", "Scanning for security headers and tokens...", "Auth Schemas Identified")}
                {renderStep(2, "Discovering endpoints", "Parsing OpenAPI paths and HTTP methods...", "Endpoints Cataloged")}
                {renderStep(3, "Extracting request schemas", "Analyzing JSON parameters and payload structures...", "Payload Types Mapped")}
                {renderStep(4, "Extracting response schemas", "Parsing successful and error payload schemas...", "Responses Modelled")}
                {renderStep(5, "Building tool definitions", "Creating LLM function calling schemas...", "Tool Definitions Built")}
              </div>

              {/* Status footer pill inside card */}
              <div className="mt-unit-8 pt-unit-4 border-t border-outline-variant/20 flex items-center justify-between">
                <span className="font-mono text-xs text-primary font-bold uppercase tracking-wider flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-primary animate-ping"></span>
                  {toolsCount > 0 ? `${toolsCount} ENDPOINTS DISCOVERED` : "SCANNING ENDPOINTS..."}
                </span>
                <span className="font-mono text-xs text-on-surface-variant">Auto-mapping parameters...</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="lg:col-span-4 flex flex-col gap-unit-6">
          <div className="bg-surface-container rounded-xl p-unit-6 border border-outline-variant/30">
            <h3 className="font-mono text-xs uppercase tracking-widest text-on-surface-variant mb-unit-4 flex items-center justify-between">
              <span>Active Connectors</span>
              <span className="w-2 h-2 rounded-full bg-secondary"></span>
            </h3>
            
            <div className="space-y-3">
              <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant/20 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-on-surface">Postgres DB_Main</p>
                  <p className="font-mono text-[11px] text-secondary">Healthy</p>
                </div>
                <span className="material-symbols-outlined text-secondary text-sm">check_circle</span>
              </div>

              <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant/20 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-on-surface">Stripe API_Prod</p>
                  <p className="font-mono text-[11px] text-secondary">Healthy</p>
                </div>
                <span className="material-symbols-outlined text-secondary text-sm">check_circle</span>
              </div>
            </div>
          </div>

          <div className="bg-surface-container rounded-xl p-unit-6 border border-outline-variant/30 bg-gradient-to-br from-surface-container to-surface-container-high relative overflow-hidden">
            <div className="absolute top-0 right-0 p-3 opacity-10 text-primary">
              <span className="material-symbols-outlined text-6xl">schema</span>
            </div>
            <h3 className="text-base font-bold text-on-surface mb-2">Tool Structuring</h3>
            <p className="text-xs text-on-surface-variant leading-relaxed mb-4">
              Learn how ToolForge maps complex nested objects into agent-ready parameters for optimal LLM function calling.
            </p>
            <button className="font-mono text-xs text-primary font-bold hover:underline uppercase tracking-wider flex items-center gap-1">
              READ GUIDE →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
