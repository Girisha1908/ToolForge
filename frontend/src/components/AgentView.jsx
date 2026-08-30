import React, { useState } from 'react';
import { apiService } from '../services/api';

export default function AgentView({ activeTools, onAgentResponse }) {
  const [inputMessage, setInputMessage] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [messages, setMessages] = useState([]);
  const [errorMsg, setErrorMsg] = useState(null);

  const handleSend = async (e) => {
    if (e) e.preventDefault();
    if (!inputMessage.trim()) return;

    const userPrompt = inputMessage.trim();
    setInputMessage('');
    setErrorMsg(null);

    // Add User Message
    const userMsgObj = { id: String(Date.now()), sender: 'user', text: userPrompt };
    setMessages(prev => [...prev, userMsgObj]);
    setIsProcessing(true);

    try {
      const response = await apiService.runAgent(userPrompt, activeTools);
      
      // Update execution timeline steps in parent if available
      if (onAgentResponse && response.steps) {
        onAgentResponse(response);
      }

      // Format agent response cards from steps and final_answer
      const agentMsgObj = {
        id: String(Date.now() + 1),
        sender: 'agent',
        success: response.success,
        finalAnswer: response.final_answer,
        steps: response.steps || [],
        toolsCalled: response.tools_called || [],
        latencyMs: response.total_latency_ms
      };

      setMessages(prev => [...prev, agentMsgObj]);
    } catch (err) {
      setErrorMsg(err.message || 'Agent execution failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="flex flex-col h-full gap-unit-4">
      {/* Agent Header */}
      <div className="flex items-center justify-between pb-unit-3 border-b border-outline-variant/30">
        <div>
          <div className="flex items-center gap-unit-2">
            <h2 className="text-xl font-bold text-on-surface">Agent Interaction</h2>
            <span className="px-2.5 py-0.5 rounded-full bg-secondary/10 border border-secondary/30 font-mono text-[10px] font-bold text-secondary uppercase tracking-wider flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
              AGENT ACTIVE
            </span>
          </div>
          <p className="text-xs text-on-surface-variant mt-1">
            Interact with the AI Agent to perform multi-step tasks using your generated API tools.
          </p>
        </div>
      </div>

      {/* Chat Conversation Scroll Area */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1 min-h-[300px]">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 border border-dashed border-outline-variant/30 rounded-xl bg-surface-container-low">
            <span className="material-symbols-outlined text-outline text-4xl mb-2">smart_toy</span>
            <h3 className="font-bold text-on-surface text-base mb-1">No agent conversation started</h3>
            <p className="text-xs text-on-surface-variant max-w-sm">
              Enter a prompt below to instruct the agent to select and execute API tools.
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className="flex flex-col gap-3">
              {msg.sender === 'user' ? (
                <div className="self-end max-w-[80%] bg-surface-container-high border border-outline-variant/30 px-4 py-2.5 rounded-xl text-sm text-on-surface font-sans shadow-sm">
                  {msg.text}
                </div>
              ) : (
                <div className="self-start w-full max-w-[95%] bg-surface-container border border-outline-variant/30 rounded-xl p-4 shadow-lg space-y-3">
                  {/* Tool execution steps */}
                  {msg.steps && msg.steps.map((step, sIdx) => (
                    <div key={sIdx} className="bg-surface-container-low p-3 rounded-lg border border-outline-variant/20 space-y-2">
                      <div className="flex items-center justify-between border-b border-outline-variant/20 pb-1.5">
                        <span className="font-mono text-xs font-bold text-primary flex items-center gap-2">
                          <span className="material-symbols-outlined text-sm">build</span>
                          Tool Call: {step.tool_name}
                        </span>
                        {step.execution_result && (
                          <span className={`font-mono text-[10px] px-2 py-0.5 rounded border ${
                            step.execution_result.success
                              ? 'bg-secondary/10 border-secondary/30 text-secondary'
                              : 'bg-error/10 border-error/30 text-error'
                          }`}>
                            HTTP {step.execution_result.status_code}
                          </span>
                        )}
                      </div>

                      {step.arguments && Object.keys(step.arguments).length > 0 && (
                        <div>
                          <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider block mb-1">
                            Arguments
                          </span>
                          <pre className="bg-surface-container-lowest p-2 rounded border border-outline-variant/20 font-mono text-[11px] text-on-surface">
                            {JSON.stringify(step.arguments, null, 2)}
                          </pre>
                        </div>
                      )}

                      {step.error && (
                        <div className="font-mono text-xs text-error bg-error/10 p-2 rounded border border-error/20">
                          {step.error}
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Final Answer */}
                  <div className="bg-primary/5 p-3.5 rounded-lg border border-primary/20 text-sm text-on-surface leading-relaxed">
                    <span className="font-mono text-[10px] text-primary font-bold uppercase tracking-wider block mb-1">
                      FINAL ANSWER
                    </span>
                    {msg.finalAnswer}
                  </div>
                </div>
              )}
            </div>
          ))
        )}

        {isProcessing && (
          <div className="self-start bg-surface-container border border-outline-variant/30 rounded-xl p-3 text-xs text-primary font-mono flex items-center gap-2 animate-pulse">
            <span className="material-symbols-outlined text-sm animate-spin">refresh</span>
            Agent analyzing request, selecting tools & executing API endpoints...
          </div>
        )}

        {errorMsg && (
          <div className="p-3 rounded-lg bg-error/10 border border-error/30 text-error font-mono text-xs">
            {errorMsg}
          </div>
        )}
      </div>

      {/* Input Box Bar */}
      <form onSubmit={handleSend} className="relative mt-auto pt-2">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Enter a prompt for the agent (e.g. Find user 42)..."
          className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl pl-4 pr-12 py-3 font-sans text-sm text-on-surface placeholder-on-surface-variant/40 focus:outline-none focus:border-primary/50 transition-colors shadow-inner"
        />
        <button
          type="submit"
          disabled={!inputMessage.trim() || isProcessing}
          className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg bg-primary text-on-primary flex items-center justify-center hover:bg-primary-container transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className="material-symbols-outlined text-sm">send</span>
        </button>
      </form>
    </div>
  );
}
