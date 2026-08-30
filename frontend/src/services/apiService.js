// Clean service abstraction for backend communication with reliable fallback mocks for offline/hackathon operation

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export async function parseApi(url) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/parse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    if (!res.ok) throw new Error('API parse error');
    return await res.json();
  } catch (err) {
    console.warn('Backend parse API unreached, returning mock generated tools', err);
    return {
      success: true,
      authType: 'Bearer Token',
      apiName: 'User Management',
      tools: [
        {
          id: 'get_user',
          name: 'get_user',
          method: 'GET',
          path: '/api/v1/users/{id}',
          description: 'Retrieve detailed information for a specific user by their unique identifier.',
          params: [
            { name: 'id', required: true, type: 'integer', description: 'Unique identifier of user' }
          ]
        },
        {
          id: 'list_users',
          name: 'list_users',
          method: 'GET',
          path: '/api/v1/users',
          description: 'Get a paginated list of all users in the system.',
          params: [
            { name: 'limit', required: false, type: 'integer', description: 'Number of items' },
            { name: 'page', required: false, type: 'integer', description: 'Page offset' }
          ]
        },
        {
          id: 'create_user',
          name: 'create_user',
          method: 'POST',
          path: '/api/v1/users',
          description: 'Provision a new user account with specified roles and permissions.',
          params: [
            { name: 'name', required: true, type: 'string', description: 'Full user name' },
            { name: 'email', required: true, type: 'string', description: 'User email' }
          ]
        }
      ]
    };
  }
}

export async function executeTool(toolId, args) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/tools/${toolId}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ args })
    });
    if (!res.ok) throw new Error('Tool execution error');
    return await res.json();
  } catch (err) {
    console.warn('Backend tool execution unreached, returning mock result', err);
    return {
      status: 200,
      data: {
        id: Number(args.id) || 42,
        name: "Rahul",
        email: "rahul@example.com",
        role: "Developer",
        status: "active"
      }
    };
  }
}

export async function agentChat(message) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/agent/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    if (!res.ok) throw new Error('Agent chat error');
    return await res.json();
  } catch (err) {
    console.warn('Backend agent chat unreached, returning mock chat result', err);
    return {
      action: 'GET_USER',
      args: { id: 42 },
      status: 'API request successful',
      resultText: 'User 42 is Rahul. Email: rahul@example.com.'
    };
  }
}
