import React, { useState } from 'react';

export default function AgentView({ onUpdateTimeline }) {
  const [inputMessage, setInputMessage] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Default pre-populated conversation match for demo
  const [messages, setMessages] = useState([
    {
      id: '1',
      sender: 'user',
      text: 'Find user 42.'
    },
    {
      id: '2',
      sender: 'agent',
      action: 'Using GET_USER',
      args: { id: 42 },
      status: 'API request successful',
      resultText: 'User 42 is Rahul. Email: rahul@example.com.'
    }
  ]);

  const handleSend = (e) => {
    if (e) e.preventDefault();
    if (!inputMessage.trim()) return;

    const userMsg = inputMessage;
    setInputMessage('');

    // Add User Message
    const userMsgObj = { id: String(Date.now()), sender: 'user', text: userMsg };
    setMessages(prev => [...prev, userMsgObj]);
    setIsProcessing(true);

    // Update execution timeline events
    if (onUpdateTimeline) {
      onUpdateTimeline([
        { title: 'User Request Received', done: true },
        { title: 'Agent Selected Tool: get_user', done: true },
        { title: 'Arguments Validated', done: true },
        { title: 'API Request Sent', done: true },
        { title: 'Response Received', done: true },
        { title: 'Result Returned to User', done: true }
      ]);
    }

    // Simulate Agent Tool Calling & Response
    setTimeout(() => {
      let agentMsg = {};
      if (userMsg.toLowerCase().includes('42')) {
        agentMsg = {
          id: String(Date.now() + 1),
          sender: 'agent',
          action: 'Using GET_USER',
          args: { id: 42 },
          status: 'API request successful',
          resultText: 'User 42 is Rahul. Email: rahul@example.com.'
        };
      } else if (userMsg.toLowerCase().includes('list') || userMsg.toLowerCase().includes('users')) {
        agentMsg = {
          id: String(Date.now() + 1),
          sender: 'agent',
          action: 'Using LIST_USERS',
          args: { limit: 10 },
          status: 'API request successful',
          resultText: 'Found 2 users: Rahul (id: 42, rahul@example.com) and Sarah (id: 43, sarah@example.com).'
        };
      } else {
        agentMsg = {
          id: String(Date.now() + 1),
          sender: 'agent',
          action: 'Using GET_USER',
          args: { id: 42 },
          status: 'API request successful',
          resultText: `Processed request for "${userMsg}". Selected tool get_user returned active user details.`
        };
      }

      setMessages(prev => [...prev, agentMsg]);
      setIsProcessing(false);
    }, 800);
  };

  return (
    <div className="flex flex-col h-full gap-unit-4">
      {/* Agent Header */}
      <div className="flex items-center justify-between pb-unit-3 border-b border-outline-variant/30">
        <div>
          <div className="flex items-center gap-unit-2">
            <h2 className="text-xl font-bold text-on-surface">Try the Agent</h2>
            <span className="px-2.5 py-0.5 rounded-full bg-secondary/10 border border-secondary/30 font-mono text-[10px] font-bold text-secondary uppercase tracking-wider flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span>
              AGENT ACTIVE
            </span>
          </div>
          <p className="text-xs text-on-surface-variant mt-1">
            Ask the agent to use your generated API tools.
          </p>
        </div>
      </div>

      {/* Chat Conversation Scroll Area */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-1">
        {messages.map((msg) => (
          <div key={msg.id} className="flex flex-col gap-2">
            {msg.sender === 'user' ? (
              /* User Bubble */
              <div className="self-end max-w-[80%] bg-surface-container-high border border-outline-variant/30 px-4 py-2.5 rounded-xl text-sm text-on-surface font-sans shadow-sm">
                {msg.text}
              </div>
            ) : (
              /* Agent Action Card */
              <div className="self-start w-full max-w-[95%] bg-surface-container border border-outline-variant/30 rounded-xl p-4 shadow-lg space-y-3">
                {/* Agent Action Badge */}
                <div className="flex items-center justify-between border-b border-outline-variant/20 pb-2">
                  <span className="font-mono text-xs font-bold text-primary flex items-center gap-2">
                    <span className="material-symbols-outlined text-sm">smart_toy</span>
                    {msg.action}
                  </span>
                  <span className="font-mono text-[10px] text-secondary bg-secondary/10 px-2 py-0.5 rounded border border-secondary/20">
                    {msg.status}
                  </span>
                </div>

                {/* Arguments Code Block */}
                <div>
                  <span className="font-mono text-[10px] text-on-surface-variant uppercase tracking-wider block mb-1">
                    Arguments
                  </span>
                  <pre className="bg-surface-container-lowest p-2.5 rounded-lg border border-outline-variant/20 font-mono text-xs text-on-surface">
                    {JSON.stringify(msg.args, null, 2)}
                  </pre>
                </div>

                {/* Final Result Text */}
                <div className="bg-surface-container-low p-3 rounded-lg border border-outline-variant/20 text-sm text-on-surface leading-relaxed">
                  {msg.resultText}
                </div>
              </div>
            )}
          </div>
        ))}

        {isProcessing && (
          <div className="self-start bg-surface-container border border-outline-variant/30 rounded-xl p-3 text-xs text-primary font-mono flex items-center gap-2 animate-pulse">
            <span className="material-symbols-outlined text-sm animate-spin">refresh</span>
            Agent selecting tool & invoking API...
          </div>
        )}
      </div>

      {/* Input Box Bar */}
      <form onSubmit={handleSend} className="relative mt-auto pt-2">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Enter a command for the agent..."
          className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl pl-4 pr-12 py-3 font-sans text-sm text-on-surface placeholder-on-surface-variant/40 focus:outline-none focus:border-primary/50 transition-colors shadow-inner"
        />
        <button
          type="submit"
          className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-lg bg-primary text-on-primary flex items-center justify-center hover:bg-primary-container transition-colors"
        >
          <span className="material-symbols-outlined text-sm">send</span>
        </button>
      </form>
    </div>
  );
}
