import React from 'react';

export function ToolList({ tools }) {
  return (
    <div>
      <h3>Generated Tools</h3>
      <ul>
        {tools?.map((t, index) => (
          <li key={index}>{t.name}</li>
        ))}
      </ul>
    </div>
  );
}
