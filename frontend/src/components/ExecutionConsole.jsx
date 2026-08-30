import React, { useState, useEffect } from 'react';
import { executeTool } from '../services/apiService';

export default function ExecutionConsole({ selectedTool, onExecute }) {
  const [argValues, setArgValues] = useState({});
  const [executionState, setExecutionState] = useState('idle'); // idle | loading | success | error
  const [responseResult, setResponseResult] = useState(null);
  const [executionResult, setExecutionResult] = useState(null); // stores the full backend ToolExecutionResult

  useEffect(() => {
    if (selectedTool) {
      const defaults = {};
      const params = selectedTool.parameters || selectedTool.params || [];
      
      params.forEach(p => {
        // Pre-populate logical defaults for the petstore test suite
        if (p.name === 'petId') {
          defaults[p.name] = '1';
        } else if (p.name === 'status') {
          defaults[p.name] = 'available';
        } else if (p.name === 'username' || p.name === 'userName') {
          defaults[p.name] = 'user1';
        } else {
          defaults[p.name] = p.default || '';
        }
      });
      
      setArgValues(defaults);
      setExecutionState('idle');
      setResponseResult(null);
      setExecutionResult(null);
    }
  }, [selectedTool]);

  const handleArgChange = (name, val) => {
    setArgValues(prev => ({ ...prev, [name]: val }));
  };

  const handleRun = async () => {
    if (!selectedTool) return;
    setExecutionState('loading');
    setResponseResult(null);
    setExecutionResult(null);
    
    try {
      const result = await executeTool(selectedTool.id, argValues);
      setExecutionResult(result);
      setResponseResult(result.response);
      setExecutionState(result.success ? 'success' : 'error');
      
      if (onExecute) {
        onExecute({ tool: selectedTool, args: argValues, result: result.response });
      }
    } catch (err) {
      console.error(err);
      setExecutionState('error');
      const errPayload = {
        success: false,
        status_code: 500,
        latency_ms: 0,
        request: { method: selectedTool.method, url: selectedTool.path },
        error: err.message
      };
      setExecutionResult(errPayload);
      setResponseResult({ error: err.message });
    }
  };

  const toolName = selectedTool ? selectedTool.name : 'No Tool Selected';
  const toolParams = selectedTool ? (selectedTool.parameters || selectedTool.params || []) : [];

  return (
    <div className="bg-surface-container rounded-xl border border-outline-variant/30 flex flex-col h-full overflow-hidden shadow-xl">
      {/* Console Header */}
      <div className="p-unit-4 border-b border-outline-variant/30 bg-surface-container-high/50 flex items-center justify-between">
        <div className="flex items-center gap-unit-2">
          <span className="material-symbols-outlined text-primary text-lg">terminal</span>
          <h3 className="font-mono text-xs uppercase tracking-widest text-on-surface font-bold">
            EXECUTION CONSOLE
          </h3>
        </div>
        {selectedTool && (
          <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-surface-container-low text-on-surface-variant border border-outline-variant/30">
            Target: {toolName}
          </span>
        )}
      </div>

      <div className="p-unit-6 flex flex-col gap-unit-6 flex-1 overflow-y-auto">
        {!selectedTool ? (
          <div className="flex-1 flex flex-col items-center justify-center text-on-surface-variant/40 py-12">
            <span className="material-symbols-outlined text-4xl mb-2">construction</span>
            <p className="font-mono text-xs uppercase tracking-wider">Select a tool to test execution</p>
          </div>
        ) : (
          <>
            {/* Tool Name Title */}
            <div>
              <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider block mb-1">
                SELECTED TOOL
              </span>
              <div className="font-mono text-lg font-bold text-primary flex items-center gap-2">
                {toolName}
                <span className="text-xs px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                  {selectedTool.method || 'GET'}
                </span>
              </div>
            </div>

            {/* Arguments Section */}
            <div className="space-y-4">
              <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider block">
                ARGUMENTS
              </span>

              {toolParams.length === 0 ? (
                <p className="text-xs text-on-surface-variant italic">No arguments required for this endpoint.</p>
              ) : (
                toolParams.map((param) => (
                  <div key={param.name} className="flex flex-col gap-1.5">
                    <div className="flex items-center justify-between">
                      <label className="font-mono text-xs text-on-surface font-semibold flex items-center gap-2">
                        <span>{param.name}</span>
                        {param.required && (
                          <span className="text-[10px] text-tertiary bg-tertiary/10 px-1.5 py-0.2 rounded font-mono uppercase">
                            REQUIRED
                          </span>
                        )}
                      </label>
                      <span className="font-mono text-[11px] text-outline">{param.type}</span>
                    </div>

                    <input
                      type="text"
                      value={argValues[param.name] ?? ''}
                      onChange={(e) => handleArgChange(param.name, e.target.value)}
                      placeholder={`Enter ${param.name}`}
                      className="w-full bg-surface-container-lowest border border-outline-variant/30 rounded-lg px-3 py-2 font-mono text-sm text-on-surface focus:outline-none focus:border-primary transition-colors"
                    />
                  </div>
                ))
              )}

              <button
                onClick={handleRun}
                disabled={executionState === 'loading'}
                className="w-full mt-2 h-11 bg-primary text-on-primary font-mono text-xs uppercase tracking-wider font-bold rounded-lg hover:bg-primary-container transition-all flex items-center justify-center gap-2 shadow-md shadow-primary/10 disabled:opacity-50"
              >
                {executionState === 'loading' ? (
                  <>
                    <span className="material-symbols-outlined text-sm animate-spin">refresh</span>
                    Executing...
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-sm">play_arrow</span>
                    Execute Tool
                  </>
                )}
              </button>
            </div>

            {/* Response Section */}
            {(executionState === 'success' || executionState === 'error') && executionResult && (
              <div className="mt-2 space-y-3 pt-4 border-t border-outline-variant/30">
                {/* Status Pill */}
                <div className="flex items-center justify-between">
                  <span className={`px-2.5 py-1 rounded font-mono text-xs font-bold flex items-center gap-1.5 ${
                    executionResult.success 
                      ? 'bg-secondary/10 border border-secondary/30 text-secondary' 
                      : 'bg-error/10 border border-error/30 text-error'
                  }`}>
                    <span className={`w-2 h-2 rounded-full ${executionResult.success ? 'bg-secondary' : 'bg-error'}`}></span>
                    {executionResult.status_code || (executionResult.success ? 200 : 500)} {executionResult.success ? 'OK' : 'ERROR'}
                  </span>
                  <span className="font-mono text-[10px] text-outline">Latency: {executionResult.latency_ms}ms</span>
                </div>

                {/* Request Display */}
                <div>
                  <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider block mb-1">
                    REQUEST
                  </span>
                  <div className="bg-surface-container-lowest p-2.5 rounded-lg border border-outline-variant/20 font-mono text-xs text-on-surface-variant space-y-1">
                    <div className="text-primary break-all">
                      {executionResult.request?.method || selectedTool.method} {executionResult.request?.url || selectedTool.path}
                    </div>
                    {selectedTool.authentication?.type && (
                      <div className="text-outline text-[11px]">
                        Authorization: {selectedTool.authentication.type}
                      </div>
                    )}
                  </div>
                </div>

                {/* Response Formatted JSON */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider">
                      RESPONSE
                    </span>
                    <span className="font-mono text-[10px] text-outline">
                      {executionResult.error ? 'error' : 'application/json'}
                    </span>
                  </div>
                  <pre className="bg-surface-container-lowest p-3 rounded-lg border border-outline-variant/20 font-mono text-xs text-secondary/90 overflow-x-auto leading-relaxed max-h-[300px]">
                    {JSON.stringify(responseResult, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
