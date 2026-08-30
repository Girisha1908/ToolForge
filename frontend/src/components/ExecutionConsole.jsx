import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';

function generateSampleJson(schema) {
  if (!schema || typeof schema !== 'object') return '';
  const props = schema.properties || {};
  if (Object.keys(props).length === 0) return '';

  const obj = {};
  for (const [key, prop] of Object.entries(props)) {
    if (prop.example !== undefined) {
      obj[key] = prop.example;
    } else if (prop.type === 'integer' || prop.type === 'number') {
      obj[key] = 1;
    } else if (prop.type === 'boolean') {
      obj[key] = true;
    } else if (prop.type === 'array') {
      obj[key] = prop.items?.example ? [prop.items.example] : ["sample_item"];
    } else if (prop.type === 'object') {
      obj[key] = {};
    } else {
      obj[key] = `sample_${key}`;
    }
  }
  return JSON.stringify(obj, null, 2);
}

export default function ExecutionConsole({ selectedTool }) {
  const [argValues, setArgValues] = useState({});
  const [jsonBodyText, setJsonBodyText] = useState('');
  const [executionState, setExecutionState] = useState('idle'); // idle | loading | success | error
  const [executionResult, setExecutionResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    if (selectedTool) {
      const defaults = {};
      const params = selectedTool.parameters || selectedTool.params || [];
      params.forEach(p => {
        defaults[p.name] = p.default !== undefined && p.default !== null ? String(p.default) : '';
      });
      setArgValues(defaults);

      // Generate initial JSON body template if tool has request_body_schema
      const bodySchema = selectedTool.request_body_schema || selectedTool.request_body;
      const initialJson = generateSampleJson(bodySchema);
      setJsonBodyText(initialJson);

      setExecutionState('idle');
      setExecutionResult(null);
      setErrorMsg(null);
    } else {
      setArgValues({});
      setJsonBodyText('');
      setExecutionState('idle');
      setExecutionResult(null);
      setErrorMsg(null);
    }
  }, [selectedTool]);

  const handleArgChange = (name, val) => {
    setArgValues(prev => ({ ...prev, [name]: val }));
  };

  const handleRun = async () => {
    if (!selectedTool) return;

    setExecutionState('loading');
    setErrorMsg(null);
    setExecutionResult(null);

    const toolId = selectedTool.id || selectedTool.name;
    const payloadArgs = { ...argValues };

    if (jsonBodyText && jsonBodyText.trim()) {
      try {
        payloadArgs._raw_body = JSON.parse(jsonBodyText.trim());
      } catch (err) {
        setExecutionState('error');
        setErrorMsg('Invalid JSON format in Request Body text area.');
        return;
      }
    }

    try {
      const result = await apiService.executeTool(toolId, payloadArgs);
      setExecutionResult(result);
      if (result.success) {
        setExecutionState('success');
      } else {
        setExecutionState('error');
        setErrorMsg(result.error || `HTTP ${result.status_code}: Request failed`);
      }
    } catch (err) {
      setExecutionState('error');
      setErrorMsg(err.message || 'Tool execution request failed.');
    }
  };

  if (!selectedTool) {
    return (
      <div className="bg-surface-container rounded-xl border border-outline-variant/30 flex flex-col h-full overflow-hidden shadow-xl p-unit-8 text-center items-center justify-center min-h-[350px]">
        <span className="material-symbols-outlined text-outline text-4xl mb-2">terminal</span>
        <h3 className="font-bold text-on-surface text-base mb-1">No tool selected</h3>
        <p className="text-xs text-on-surface-variant max-w-xs">
          Select a generated tool from the list to inspect parameters and test execution.
        </p>
      </div>
    );
  }

  const toolName = selectedTool.name || 'unnamed_tool';
  const toolParams = selectedTool.parameters || selectedTool.params || [];
  const hasBodySchema = Boolean(selectedTool.request_body_schema || selectedTool.request_body) || ['POST', 'PUT', 'PATCH'].includes(selectedTool.method);

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
              {selectedTool.method || 'GET'}
            </span>
          </div>
        </div>

        {/* Arguments Section */}
        <div className="space-y-4">
          <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider block">
            ARGUMENTS
          </span>

          {toolParams.length === 0 && !hasBodySchema ? (
            <p className="text-xs text-on-surface-variant italic font-mono">No parameters required for this endpoint.</p>
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
                  <span className="font-mono text-[11px] text-outline">{param.type || 'string'}</span>
                </div>

                <input
                  type="text"
                  value={argValues[param.name] || ''}
                  onChange={(e) => handleArgChange(param.name, e.target.value)}
                  placeholder={param.description || `Enter ${param.name}`}
                  className="w-full bg-surface-container-lowest border border-outline-variant/30 rounded-lg px-3 py-2 font-mono text-sm text-on-surface focus:outline-none focus:border-primary transition-colors"
                />
              </div>
            ))
          )}

          {/* Request Body JSON Text Area for POST / PUT / PATCH endpoints */}
          {hasBodySchema && (
            <div className="flex flex-col gap-1.5 pt-2 border-t border-outline-variant/20">
              <div className="flex items-center justify-between">
                <label className="font-mono text-xs text-on-surface font-semibold flex items-center gap-2">
                  <span>Request Body (JSON)</span>
                  <span className="text-[10px] text-primary bg-primary/10 px-1.5 py-0.2 rounded font-mono uppercase">
                    APPLICATION/JSON
                  </span>
                </label>
              </div>

              <textarea
                rows={6}
                value={jsonBodyText}
                onChange={(e) => setJsonBodyText(e.target.value)}
                placeholder='{\n  "key": "value"\n}'
                className="w-full bg-surface-container-lowest border border-outline-variant/30 rounded-lg p-3 font-mono text-xs text-on-surface focus:outline-none focus:border-primary transition-colors leading-relaxed"
              />
            </div>
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

        {/* Error Notification */}
        {executionState === 'error' && errorMsg && (
          <div className="p-3 rounded-lg bg-error/10 border border-error/30 text-error font-mono text-xs">
            {errorMsg}
          </div>
        )}

        {/* Response Section */}
        {executionResult && (
          <div className="mt-2 space-y-3 pt-4 border-t border-outline-variant/30">
            <div className="flex items-center justify-between">
              <span className={`px-2.5 py-1 rounded font-mono text-xs font-bold border flex items-center gap-1.5 ${
                executionResult.success
                  ? 'bg-secondary/10 border-secondary/30 text-secondary'
                  : 'bg-error/10 border-error/30 text-error'
              }`}>
                <span className={`w-2 h-2 rounded-full ${executionResult.success ? 'bg-secondary' : 'bg-error'}`}></span>
                HTTP {executionResult.status_code}
              </span>
              <span className="font-mono text-[10px] text-outline">
                Latency: {executionResult.latency_ms}ms
              </span>
            </div>

            {/* Request Display */}
            {executionResult.request && (
              <div>
                <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider block mb-1">
                  REQUEST
                </span>
                <div className="bg-surface-container-lowest p-2.5 rounded-lg border border-outline-variant/20 font-mono text-xs text-on-surface-variant space-y-1">
                  <div className="text-primary">
                    {executionResult.request.method} {executionResult.request.url || executionResult.request.path}
                  </div>
                </div>
              </div>
            )}

            {/* Response Formatted JSON */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider">
                  RESPONSE
                </span>
                <span className="font-mono text-[10px] text-outline">
                  {typeof executionResult.response === 'object' ? 'application/json' : 'text/plain'}
                </span>
              </div>
              <pre className="bg-surface-container-lowest p-3 rounded-lg border border-outline-variant/20 font-mono text-xs text-secondary/90 overflow-x-auto leading-relaxed">
                {typeof executionResult.response === 'object'
                  ? JSON.stringify(executionResult.response, null, 2)
                  : String(executionResult.response || executionResult.error || 'No body')}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
