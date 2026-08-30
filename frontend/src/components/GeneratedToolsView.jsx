import React from 'react';

export default function GeneratedToolsView({ tools, selectedTool, onSelectTool, onOpenAgent }) {
  const toolList = tools || [];

  return (
    <div className="flex flex-col gap-unit-6">
      {/* Header Info */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-bold text-on-surface">Generated Tools</h2>
          {toolList.length > 0 && (
            <button 
              onClick={onOpenAgent}
              className="px-4 py-2 bg-secondary/10 border border-secondary/30 text-secondary hover:bg-secondary/20 rounded-lg font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all shadow-sm"
            >
              <span className="material-symbols-outlined text-sm">smart_toy</span>
              Try the Agent →
            </button>
          )}
        </div>
        <p className="text-xs text-on-surface-variant max-w-xl">
          Agent-ready tool capabilities generated from API endpoints.
        </p>
      </div>

      {/* Summary Pills */}
      {toolList.length > 0 && (
        <div className="flex items-center gap-unit-4 flex-wrap pb-unit-2 border-b border-outline-variant/20">
          <span className="px-3 py-1 bg-surface-container-high border border-outline-variant/30 rounded-full font-mono text-xs text-primary font-bold">
            {toolList.length} TOOLS GENERATED
          </span>
        </div>
      )}

      {/* Tool Cards or Empty State */}
      {toolList.length === 0 ? (
        <div className="p-unit-8 rounded-xl border border-dashed border-outline-variant/40 bg-surface-container-low text-center flex flex-col items-center justify-center min-h-[220px]">
          <span className="material-symbols-outlined text-outline text-4xl mb-2">build</span>
          <h3 className="font-bold text-on-surface text-base mb-1">No tools generated yet</h3>
          <p className="text-xs text-on-surface-variant max-w-sm">
            Start by analyzing an API documentation URL to generate executable tools.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-unit-4">
          {toolList.map((tool) => {
            const toolId = tool.id || tool.name;
            const isSelected = selectedTool && (selectedTool.id === toolId || selectedTool.name === tool.name);
            return (
              <div
                key={toolId}
                onClick={() => onSelectTool(tool)}
                className={`p-unit-6 rounded-xl border transition-all cursor-pointer relative ${
                  isSelected
                    ? 'bg-surface-container border-primary shadow-lg ring-1 ring-primary/40'
                    : 'bg-surface-container-low border-outline-variant/20 hover:border-outline-variant/50 hover:bg-surface-container'
                }`}
              >
                {isSelected && (
                  <div className="absolute top-0 right-0 w-2 h-full bg-primary rounded-r-xl"></div>
                )}

                <div className="flex items-start justify-between mb-unit-3">
                  <div className="flex items-center gap-unit-3">
                    <span className="font-mono text-sm font-bold text-on-surface">
                      {tool.name}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                        tool.method === 'GET'
                          ? 'bg-primary/20 text-primary border border-primary/30'
                          : tool.method === 'POST'
                          ? 'bg-secondary/20 text-secondary border border-secondary/30'
                          : 'bg-tertiary/20 text-tertiary border border-tertiary/30'
                      }`}
                    >
                      {tool.method}
                    </span>
                  </div>

                  <span className="material-symbols-outlined text-on-surface-variant text-sm">
                    {isSelected ? 'radio_button_checked' : 'radio_button_unchecked'}
                  </span>
                </div>

                <p className="text-xs text-on-surface-variant mb-unit-4 leading-relaxed">
                  {tool.description}
                </p>

                <div className="font-mono text-xs text-outline bg-surface-container-lowest px-3 py-1.5 rounded border border-outline-variant/20 inline-block">
                  {tool.path}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
