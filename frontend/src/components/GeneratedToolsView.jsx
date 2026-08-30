import React from 'react';

export default function GeneratedToolsView({ tools, selectedTool, onSelectTool, onOpenAgent }) {
  const defaultTools = [
    {
      id: 'get_user',
      name: 'get_user',
      method: 'GET',
      path: '/api/v1/users/{id}',
      description: 'Retrieve detailed information for a specific user by their unique identifier.',
      params: [
        { name: 'id', required: true, type: 'integer', description: 'Unique identifier of the user account' }
      ]
    },
    {
      id: 'list_users',
      name: 'list_users',
      method: 'GET',
      path: '/api/v1/users',
      description: 'Get a paginated list of all users in the system.',
      params: [
        { name: 'limit', required: false, type: 'integer', description: 'Number of items to return' },
        { name: 'page', required: false, type: 'integer', description: 'Page number offset' }
      ]
    },
    {
      id: 'create_user',
      name: 'create_user',
      method: 'POST',
      path: '/api/v1/users',
      description: 'Provision a new user account with specified roles and permissions.',
      params: [
        { name: 'name', required: true, type: 'string', description: 'Full name of user' },
        { name: 'email', required: true, type: 'string', description: 'Email address' }
      ]
    }
  ];

  const toolList = tools && tools.length > 0 ? tools : defaultTools;

  return (
    <div className="flex flex-col gap-unit-6">
      {/* Header Info */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-bold text-on-surface">Generated Tools</h2>
          <button 
            onClick={onOpenAgent}
            className="px-4 py-2 bg-secondary/10 border border-secondary/30 text-secondary hover:bg-secondary/20 rounded-lg font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all shadow-sm"
          >
            <span className="material-symbols-outlined text-sm">smart_toy</span>
            Try the Agent →
          </button>
        </div>
        <p className="text-xs text-on-surface-variant max-w-xl">
          Agent-ready capabilities generated from your API. These tools are verified and ready for deployment to your AI agents.
        </p>
      </div>

      {/* Summary Pills */}
      <div className="flex items-center gap-unit-4 flex-wrap pb-unit-2 border-b border-outline-variant/20">
        <span className="px-3 py-1 bg-surface-container-high border border-outline-variant/30 rounded-full font-mono text-xs text-primary font-bold">
          {toolList.length} TOOLS GENERATED
        </span>
        <span className="px-3 py-1 bg-surface-container-high border border-outline-variant/30 rounded-full font-mono text-xs text-on-surface-variant">
          Auth: Bearer Token
        </span>
        <span className="px-3 py-1 bg-surface-container-high border border-outline-variant/30 rounded-full font-mono text-xs text-on-surface-variant">
          API: User Management
        </span>
      </div>

      {/* Tool Cards */}
      <div className="flex flex-col gap-unit-4">
        {toolList.map((tool) => {
          const isSelected = selectedTool && selectedTool.id === tool.id;
          return (
            <div
              key={tool.id}
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
    </div>
  );
}
