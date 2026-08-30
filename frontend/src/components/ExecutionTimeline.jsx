import React from 'react';

export default function ExecutionTimeline({ steps }) {
  const defaultSteps = [
    { title: 'User Request Received', done: true },
    { title: 'Agent Selected Tool: get_user', done: true },
    { title: 'Arguments Validated', done: true },
    { title: 'API Request Sent', done: true },
    { title: 'Response Received', done: true },
    { title: 'Result Returned to User', done: false }
  ];

  const currentSteps = steps && steps.length > 0 ? steps : defaultSteps;

  return (
    <div className="bg-surface-container rounded-xl border border-outline-variant/30 p-unit-6 flex flex-col h-full shadow-xl">
      <div className="flex items-center justify-between pb-unit-4 border-b border-outline-variant/30 mb-unit-6">
        <h3 className="font-mono text-xs uppercase tracking-widest text-on-surface font-bold flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-base">route</span>
          Execution Flow
        </h3>
        <span className="font-mono text-[10px] text-secondary bg-secondary/10 px-2 py-0.5 rounded border border-secondary/20">
          LIVE
        </span>
      </div>

      <div className="flex-1 flex flex-col gap-unit-6 relative">
        {currentSteps.map((step, idx) => (
          <div key={idx} className="flex items-start gap-unit-4 relative group">
            {/* Connecting line */}
            {idx < currentSteps.length - 1 && (
              <div 
                className={`absolute left-3 top-6 bottom-[-24px] w-[2px] ${
                  step.done ? 'bg-secondary/40' : 'bg-outline-variant/20'
                }`}
              ></div>
            )}

            <div className="mt-0.5 flex-shrink-0 z-10">
              {step.done ? (
                <div className="w-6 h-6 rounded-full bg-secondary/20 border border-secondary/50 flex items-center justify-center text-secondary">
                  <span className="material-symbols-outlined text-[14px]">check</span>
                </div>
              ) : (
                <div className="w-6 h-6 rounded-full bg-surface-variant border border-outline-variant flex items-center justify-center">
                  <div className="w-2 h-2 rounded-full bg-outline-variant"></div>
                </div>
              )}
            </div>

            <div className="flex-1">
              <p
                className={`font-mono text-xs ${
                  step.done ? 'text-on-surface font-medium' : 'text-on-surface-variant opacity-60'
                }`}
              >
                {step.title}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
