const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiService {
  async parseDocumentation(url) {
    const res = await fetch(`${API_BASE_URL}/api/parse-doc`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Failed to parse documentation (HTTP ${res.status})`);
    }
    return res.json();
  }

  async generateTools(url, spec = null) {
    const payload = spec ? { spec } : { url };
    const res = await fetch(`${API_BASE_URL}/api/generate-tools`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Failed to generate tools (HTTP ${res.status})`);
    }
    return res.json();
  }

  async listTools() {
    const res = await fetch(`${API_BASE_URL}/api/tools`);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Failed to list tools (HTTP ${res.status})`);
    }
    return res.json();
  }

  async getTool(toolId) {
    const res = await fetch(`${API_BASE_URL}/api/tools/${encodeURIComponent(toolId)}`);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Tool not found (HTTP ${res.status})`);
    }
    return res.json();
  }

  async executeTool(toolId, args) {
    const res = await fetch(`${API_BASE_URL}/api/tools/${encodeURIComponent(toolId)}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ arguments: args })
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Tool execution failed (HTTP ${res.status})`);
    }
    return res.json();
  }

  async runAgent(message, tools = null, maxIterations = 5) {
    const res = await fetch(`${API_BASE_URL}/api/agent/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        tools,
        max_iterations: maxIterations
      })
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Agent runtime error (HTTP ${res.status})`);
    }
    return res.json();
  }
}

export const apiService = new ApiService();
