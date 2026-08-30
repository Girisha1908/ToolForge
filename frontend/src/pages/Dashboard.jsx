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
  const [apiName, setApiName] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [tools, setTools] = useState([]);
  const [selectedTool, setSelectedTool] = useState(null);
  const [timelineSteps, setTimelineSteps] = useState([]);

  const handleStartAnalysis = (url) => {
    setApiUrl(url);
    setAppState('ANALYZING');
  };

  const handleAnalysisComplete = (connector) => {
    const generatedTools = connector?.tools || [];
    setTools(generatedTools);
    setApiName(connector?.api_name || 'Parsed API');
    setTimelineSteps([]); // Reset timeline steps from previous sessions
    if (generatedTools.length > 0) {
      setSelectedTool(generatedTools[0]);
    } else {
      setSelectedTool(null);
    }
    setAppState('GENERATED_TOOLS');
  };

  const handleAnalysisError = (msg) => {
    setErrorMsg(msg);
    setAppState('ERROR');
  };

  const handleAgentResponse = (agentResponse) => {
    if (agentResponse && agentResponse.steps) {
      const formattedSteps = agentResponse.steps.map((step) => {
        const isSuccess = step.execution_result ? step.execution_result.success : !step.error;
        return {
          title: `Tool: ${step.tool_name} (${isSuccess ? 'Success' : 'Error'})`,
          done: true,
          success: isSuccess,
          error: step.error
        };
      });

      if (agentResponse.final_answer) {
        formattedSteps.push({
          title: 'Final Answer Generated',
          done: true,
          success: agentResponse.success
        });
      }

      setTimelineSteps(formattedSteps);
    }
  };

  const handleReset = () => {
    setAppState('IDLE');
    setApiUrl('');
    setApiName('');
    setErrorMsg('');
    setTools([]);
    setSelectedTool(null);
    setTimelineSteps([]);
  };

  if (activeTab === 'documentation') {
    return (
      <div className="max-w-container-max mx-auto px-unit-8 py-24">
        <h2 className="text-2xl font-bold text-on-surface mb-2">ToolForge Documentation</h2>
        <p className="text-sm text-on-surface-variant mb-6">Learn how ToolForge automatically generates executable agent tools from API documentation.</p>
        <div className="bg-surface-container p-6 rounded-xl border border-outline-variant/30 font-mono text-xs text-on-surface-variant space-y-4">
          <p className="text-primary font-bold">// 1. Provide API documentation URL (OpenAPI, Swagger, Postman, HTML)</p>
          <p>// 2. ToolForge ingests endpoints, parameter schemas, and authentication</p>
          <p>// 3. Generates validated tool definitions registered in ToolRegistry</p>
          <p>// 4. Executes dynamic HTTP requests through secure executor & Agent Runtime</p>
        </div>
      </div>
    );
  }

  return (
    <main className="w-full min-h-screen">
      {/* IDLE state -> Landing View */}
      {appState === 'IDLE' && (
        <LandingView
          onAnalyze={handleStartAnalysis}
        />
      )}

      {/* ANALYZING state -> Progress Analysis */}
      {appState === 'ANALYZING' && (
        <AnalysisView
          url={apiUrl}
          onComplete={handleAnalysisComplete}
          onError={handleAnalysisError}
          onCancel={handleReset}
        />
      )}

      {/* GENERATED_TOOLS state -> Two Column: Tool Cards + Execution Console */}
      {appState === 'GENERATED_TOOLS' && (
        <div className="max-w-container-max mx-auto px-unit-8 py-8 pt-20">
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-outline-variant/30">
            <div>
              <span className="font-mono text-xs text-on-surface-variant uppercase tracking-widest">
                API WORKSPACE: {apiName.toUpperCase()}
              </span>
              <h1 className="text-2xl font-bold text-on-surface">API Tools Workspace</h1>
            </div>

            <div className="flex items-center gap-3">
              {tools.length > 0 && (
                <button
                  onClick={() => setAppState('AGENT')}
                  className="px-4 py-2 bg-primary text-on-primary rounded-lg font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-lg shadow-primary/20 hover:bg-primary-container transition-all"
                >
                  <span className="material-symbols-outlined text-sm">smart_toy</span>
                  TRY AGENT MODE
                </button>
              )}
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
              />
            </div>
          </div>
        </div>
      )}

      {/* AGENT state -> Two Column: Agent Console + Execution Timeline */}
      {appState === 'AGENT' && (
        <div className="max-w-container-max mx-auto px-unit-8 py-8 pt-20">
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-outline-variant/30">
            <div>
              <span className="font-mono text-xs text-on-surface-variant uppercase tracking-widest">
                AGENT CONSOLE: {apiName.toUpperCase()}
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
              <AgentView
                activeTools={tools}
                onAgentResponse={handleAgentResponse}
              />
            </div>
            <div className="lg:col-span-5 h-full">
              <ExecutionTimeline steps={timelineSteps} />
            </div>
          </div>
        </div>
      )}

      {/* ERROR state -> Error View */}
      {appState === 'ERROR' && (
        <ErrorView
          errorMsg={errorMsg}
          onTryAnother={handleReset}
        />
      )}
    </main>
  );
}
