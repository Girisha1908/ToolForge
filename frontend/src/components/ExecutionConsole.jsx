import React, { useState, useEffect } from 'react';

export default function ExecutionConsole({ selectedTool, onExecute }) {
  const [argValues, setArgValues] = useState({ id: '42' });
  const [executionState, setExecutionState] = useState('idle'); // idle | loading | success | error
  const [responseResult, setResponseResult] = useState(null);

  useEffect(() => {
    if (selectedTool) {
      // Set default argument values based on selected tool
      const defaults = {};
      if (selectedTool.params) {
        selectedTool.params.forEach(p => {
          defaults[p.name] = p.name === 'id' ? '42' : 'sample_value';
        });
      } else {
        defaults['id'] = '42';
      }
      setArgValues(defaults);
      setExecutionState('idle');
      setResponseResult(null);
    }
  }, [selectedTool]);

  const handleArgChange = (name, val) => {
    setArgValues(prev => ({ ...prev, [name]: val }));
  };

  const handleRun = async () => {
    setExecutionState('loading');
    
    // Simulate real backend API round-trip execution
    setTimeout(() => {
      const toolName = selectedTool ? selectedTool.name : 'get_user';
      const idVal = argValues['id'] || '42';
      
      let resData = {};
      if (toolName === 'get_user') {
        resData = {
          id: Number(idVal) || 42,
          name: "Rahul",
          email: "rahul@example.com",
          role: "Developer",
          status: "active",
          created_at: "2026-01-15T09:30:00Z"
        };
      } else if (toolName === 'list_users') {
        resData = {
          total: 2,
          users: [
            { id: 42, name: "Rahul", email: "rahul@example.com" },
            { id: 43, name: "Sarah", email: "sarah@example.com" }
          ]
        };
      } else {
        resData = {
          status: "created",
          user: { id: 99, ...argValues }
        };
      }

      setResponseResult(resData);
      setExecutionState('success');
      if (onExecute) {
        onExecute({ tool: selectedTool, args: argValues, result: resData });
      }
    }, 600);
  };

  const toolName = selectedTool ? selectedTool.name : 'get_user';
  const toolParams = selectedTool?.params || [
    { name: 'id', required: true, type: 'integer', description: 'Unique identifier of user' }
  ];

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
        <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-surface-container-low text-on-surface-variant border border-outline-variant/30">
          Target: {toolName}
        </span>
      </div>

      <div className="p-unit-6 flex flex-col gap-unit-6 flex-1 overflow-y-auto">
        {/* Tool Name Title */}
        <div>
          <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider block mb-1">
            SELECTED TOOL
          </span>
          <div className="font-mono text-lg font-bold text-primary flex items-center gap-2">
            {toolName}
            <span className="text-xs px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
              {selectedTool?.method || 'GET'}
            </span>
          </div>
        </div>

        {/* Arguments Section */}
        <div className="space-y-4">
          <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider block">
            ARGUMENTS
          </span>

          {toolParams.map((param) => (
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
                value={argValues[param.name] || ''}
                onChange={(e) => handleArgChange(param.name, e.target.value)}
                placeholder={`Enter ${param.name}`}
                className="w-full bg-surface-container-lowest border border-outline-variant/30 rounded-lg px-3 py-2 font-mono text-sm text-on-surface focus:outline-none focus:border-primary transition-colors"
              />
            </div>
          ))}

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
        {executionState === 'success' && responseResult && (
          <div className="mt-2 space-y-3 pt-4 border-t border-outline-variant/30">
            {/* Status Pill */}
            <div className="flex items-center justify-between">
              <span className="px-2.5 py-1 rounded bg-secondary/10 border border-secondary/30 font-mono text-xs font-bold text-secondary flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-secondary"></span>
                200 OK
              </span>
              <span className="font-mono text-[10px] text-outline">Latency: 124ms</span>
            </div>

            {/* Request Display */}
            <div>
              <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider block mb-1">
                REQUEST
              </span>
              <div className="bg-surface-container-lowest p-2.5 rounded-lg border border-outline-variant/20 font-mono text-xs text-on-surface-variant space-y-1">
                <div className="text-primary">
                  {selectedTool?.method || 'GET'} {selectedTool?.path?.replace('{id}', argValues['id'] || '42') || `/api/v1/users/${argValues['id'] || '42'}`}
                </div>
                <div className="text-outline text-[11px]">Authorization: Bearer ***</div>
              </div>
            </div>

            {/* Response Formatted JSON */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider">
                  RESPONSE
                </span>
                <span className="font-mono text-[10px] text-outline">application/json</span>
              </div>
              <pre className="bg-surface-container-lowest p-3 rounded-lg border border-outline-variant/20 font-mono text-xs text-secondary/90 overflow-x-auto leading-relaxed">
                {JSON.stringify(responseResult, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
