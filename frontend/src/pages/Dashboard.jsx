import React, { useState } from 'react';
import LandingView from '../components/LandingView';
import AnalysisView from '../components/AnalysisView';
import GeneratedToolsView from '../components/GeneratedToolsView';
import ExecutionConsole from '../components/ExecutionConsole';
import AgentView from '../components/AgentView';
import ExecutionTimeline from '../components/ExecutionTimeline';
import ErrorView from '../components/ErrorView';

export default function Dashboard({ activeTab }) {
  // App State: IDLE | ANALYZING | GENERATED_TOOLS | AGENT | ERROR
  const [appState, setAppState] = useState('IDLE');
  const [apiUrl, setApiUrl] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [selectedTool, setSelectedTool] = useState(null);
  const [tools, setTools] = useState([]);
  const [apiName, setApiName] = useState('');
  const [authType, setAuthType] = useState('');

  const [timelineSteps, setTimelineSteps] = useState([
    { title: 'User Request Received', done: true },
    { title: 'Agent Selected Tool: get_user', done: true },
    { title: 'Arguments Validated', done: true },
    { title: 'API Request Sent', done: true },
    { title: 'Response Received', done: true },
    { title: 'Result Returned to User', done: true }
  ]);

  const handleStartAnalysis = (url) => {
    setApiUrl(url);
    setAppState('ANALYZING');
  };

  const handleTriggerError = (url, customMsg) => {
    setApiUrl(url);
    setErrorMsg(customMsg || `The API documentation at ${url} could not be parsed. Ensure the URL is public and follows OpenAPI 3.0+ specifications.`);
    setAppState('ERROR');
  };

  const handleAnalysisComplete = (data) => {
    if (data) {
      setTools(data.tools || []);
      setApiName(data.apiName || '');
      setAuthType(data.authType || '');
      if (data.tools && data.tools.length > 0) {
        setSelectedTool(data.tools[0]);
      }
    }
    setAppState('GENERATED_TOOLS');
  };

  const handleReset = () => {
    setAppState('IDLE');
    setApiUrl('');
    setErrorMsg('');
    setTools([]);
    setSelectedTool(null);
    setApiName('');
    setAuthType('');
  };

  // Render view depending on navigation tab & state
  if (activeTab === 'connectors') {
    return (
      <div className="max-w-container-max mx-auto px-unit-8 py-24 text-center">
        <h2 className="text-2xl font-bold text-on-surface mb-2">Connectors Directory</h2>
        <p className="text-sm text-on-surface-variant mb-8">Manage active API integrations and webhook listeners.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-surface-container p-6 rounded-xl border border-outline-variant/30 text-left">
            <h3 className="font-bold text-lg mb-1">Postgres DB_Main</h3>
            <span className="text-xs font-mono text-secondary">STATUS: HEALTHY</span>
          </div>
          <div className="bg-surface-container p-6 rounded-xl border border-outline-variant/30 text-left">
            <h3 className="font-bold text-lg mb-1">Stripe API_Prod</h3>
            <span className="text-xs font-mono text-secondary">STATUS: HEALTHY</span>
          </div>
          <div className="bg-surface-container p-6 rounded-xl border border-outline-variant/30 text-left">
            <h3 className="font-bold text-lg mb-1">Custom OpenAPI Endpoint</h3>
            <span className="text-xs font-mono text-primary">STATUS: CONNECTED</span>
          </div>
        </div>
      </div>
    );
  }

  if (activeTab === 'documentation') {
    return (
      <div className="max-w-container-max mx-auto px-unit-8 py-24">
        <h2 className="text-2xl font-bold text-on-surface mb-2">ToolForge Documentation</h2>
        <p className="text-sm text-on-surface-variant mb-6">Learn how ToolForge automatically generates function calling schemas for LLM agent frameworks.</p>
        <div className="bg-surface-container p-6 rounded-xl border border-outline-variant/30 font-mono text-xs text-on-surface-variant space-y-4">
          <p className="text-primary font-bold">// 1. Paste OpenAPI URL</p>
          <p>// 2. ToolForge parses endpoints and parameter constraints</p>
          <p>// 3. Tools are exported as JSON Schema compatible with OpenAI, LangChain & LlamaIndex</p>
        </div>
      </div>
    );
  }

  return (
    <main className="w-full min-h-screen">
      {/* IDLE state -> Landing Page */}
      {appState === 'IDLE' && (
        <LandingView
          onAnalyze={handleStartAnalysis}
          onTriggerError={handleTriggerError}
        />
      )}

      {/* ANALYZING state -> Progress Checklist */}
      {appState === 'ANALYZING' && (
        <AnalysisView
          url={apiUrl}
          onComplete={handleAnalysisComplete}
          onTriggerError={handleTriggerError}
          onCancel={handleReset}
        />
      )}

      {/* GENERATED_TOOLS state -> Two Column: Tool Cards + Execution Console */}
      {appState === 'GENERATED_TOOLS' && (
        <div className="max-w-container-max mx-auto px-unit-8 py-8 pt-20">
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-outline-variant/30">
            <div>
              <span className="font-mono text-xs text-on-surface-variant uppercase tracking-widest">
                PROJECT: TOOLFORGE_DEMO
              </span>
              <h1 className="text-2xl font-bold text-on-surface">API Tools Workspace</h1>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setAppState('AGENT')}
                className="px-4 py-2 bg-primary text-on-primary rounded-lg font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-lg shadow-primary/20 hover:bg-primary-container transition-all"
              >
                <span className="material-symbols-outlined text-sm">smart_toy</span>
                TRY AGENT MODE
              </button>
              <button
                onClick={handleReset}
                className="px-3 py-2 bg-surface-container border border-outline-variant/30 text-on-surface-variant hover:text-on-surface rounded-lg font-mono text-xs uppercase"
              >
                Reset
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-unit-6">
            <div className="lg:col-span-7">
              <GeneratedToolsView
                tools={tools}
                selectedTool={selectedTool}
                onSelectTool={setSelectedTool}
                onOpenAgent={() => setAppState('AGENT')}
              />
            </div>
            <div className="lg:col-span-5 min-h-[500px]">
              <ExecutionConsole
                selectedTool={selectedTool}
                onExecute={() => {}}
              />
            </div>
          </div>
        </div>
      )}

      {/* AGENT state -> Two Column: Agent Console + Execution Timeline Flow */}
      {appState === 'AGENT' && (
        <div className="max-w-container-max mx-auto px-unit-8 py-8 pt-20">
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-outline-variant/30">
            <div>
              <span className="font-mono text-xs text-on-surface-variant uppercase tracking-widest">
                AGENT CONSOLE
              </span>
              <h1 className="text-2xl font-bold text-on-surface">AI Agent Execution Environment</h1>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setAppState('GENERATED_TOOLS')}
                className="px-4 py-2 bg-surface-container border border-outline-variant/30 text-on-surface rounded-lg font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-2 hover:bg-surface-container-high transition-colors"
              >
                <span className="material-symbols-outlined text-sm">build</span>
                VIEW GENERATED TOOLS
              </button>
              <button
                onClick={handleReset}
                className="px-3 py-2 bg-surface-container border border-outline-variant/30 text-on-surface-variant hover:text-on-surface rounded-lg font-mono text-xs uppercase"
              >
                Reset
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-unit-6 min-h-[550px]">
            <div className="lg:col-span-7 h-full">
              <AgentView onUpdateTimeline={setTimelineSteps} />
            </div>
            <div className="lg:col-span-5 h-full">
              <ExecutionTimeline steps={timelineSteps} />
            </div>
          </div>
        </div>
      )}

      {/* ERROR state -> Centered Error Card */}
      {appState === 'ERROR' && (
        <ErrorView
          errorMsg={errorMsg}
          onTryAnother={handleReset}
        />
      )}
    </main>
  );
}
