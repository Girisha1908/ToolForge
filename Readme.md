# 🔨 ToolForge

### Turn API documentation into tools your AI agents can actually use.

ToolForge is an AI-powered universal API adapter that transforms API documentation into **agent-ready tools**.

Instead of manually reading API documentation, understanding authentication, mapping request parameters, defining schemas, and writing custom wrappers for every API, ToolForge automates the process.

Give ToolForge an API/OpenAPI documentation URL → ToolForge understands the API → generates tool definitions → and allows an AI agent to use those tools to interact with the API.

---

## 🚀 The Problem

AI agents are becoming increasingly capable, but an agent is only as useful as the tools it can access.

Connecting an AI agent to an API usually requires a developer to manually understand and implement:

* Authentication
* API endpoints
* HTTP methods
* Request parameters
* Request body schemas
* Response structures
* Error formats
* Pagination
* API-specific conventions

Every API is different.

For example, connecting an agent to Twilio requires understanding Twilio's authentication, endpoints, parameters, request formats, and responses.

Connecting the same agent to GitHub requires an entirely different integration.

Connecting it to Jira, Notion, Stripe, AWS, or another service requires another custom integration.

This creates a growing problem:

> **AI agents need tools, but creating those tools is still largely manual.**

---

# 💡 Our Solution

ToolForge acts as a universal adapter between APIs and AI agents.

Instead of manually creating an integration, a developer provides an API's documentation or OpenAPI specification.

```text
API Documentation
       ↓
   ToolForge
       ↓
Understand API
       ↓
Normalize API
       ↓
Generate Agent Tools
       ↓
Register Tools
       ↓
AI Agent
       ↓
Execute API Calls
```

For example, given an API containing:

```text
GET    /users
GET    /users/{id}
POST   /users
DELETE /users/{id}
```

ToolForge can generate agent-friendly tools such as:

```text
list_users()
get_user(id)
create_user(name, email)
delete_user(id)
```

The agent can then reason about which tool it needs and invoke it.

---

# 🎯 Example

Imagine an API provides user-management functionality.

A developer provides:

```text
https://example.com/api/docs
```

ToolForge analyzes the API and discovers:

```text
✓ Authentication
✓ Endpoints
✓ Request parameters
✓ Request schemas
✓ Response schemas
✓ HTTP methods
```

It then produces:

```text
Generated Tools

✓ list_users()
✓ get_user(id)
✓ create_user(name, email)
✓ delete_user(id)
```

Now the user can interact with an AI agent using natural language.

### User

> Find user 42.

### Agent

The agent determines that `get_user()` is the appropriate tool.

```text
get_user(id=42)
```

ToolForge translates that tool invocation into the appropriate API request:

```text
GET /users/42
```

The API responds:

```json
{
  "id": 42,
  "name": "Rahul",
  "email": "rahul@example.com"
}
```

The agent can then present the result to the user.

---

# 🔥 Why ToolForge?

Without ToolForge:

```text
New API
   ↓
Read documentation
   ↓
Understand authentication
   ↓
Understand endpoints
   ↓
Write wrapper functions
   ↓
Define schemas
   ↓
Test integration
   ↓
Connect to agent
```

With ToolForge:

```text
API Documentation
       ↓
   ToolForge
       ↓
Agent-ready tools
       ↓
AI Agent
```

The goal is to reduce API-to-agent integration from a manual development task to an automated workflow.

---

# 🧠 How It Works

ToolForge is built around a simple pipeline.

## 1. API Ingestion

The user provides an API documentation or OpenAPI URL.

```text
https://api.example.com/openapi.json
```

ToolForge retrieves and processes the API specification.

---

## 2. API Analysis

The API specification is analyzed to identify:

* API name
* Base URL
* Authentication requirements
* Available endpoints
* HTTP methods
* Path parameters
* Query parameters
* Request bodies
* Response schemas
* Endpoint descriptions

Example:

```text
GET /users/{id}

Description:
Retrieve a user by ID.

Parameters:
id: integer

Response:
User object
```

---

## 3. Normalization

Different APIs describe their capabilities in different ways.

ToolForge converts the discovered information into a normalized internal representation.

Conceptually:

```text
Normalized API

API
├── name
├── base_url
├── authentication
└── endpoints
    ├── name
    ├── description
    ├── method
    ├── path
    ├── parameters
    ├── request_body
    └── response
```

This normalized representation creates a common interface between different APIs and the agent runtime.

---

## 4. Tool Generation

Each API endpoint is converted into an agent-friendly tool.

For example:

```text
GET /users/{id}
```

becomes:

```text
get_user(id)
```

And:

```text
POST /users
```

becomes:

```text
create_user(name, email)
```

The important part is that the agent doesn't need to understand the underlying HTTP implementation.

It simply sees tools it knows how to use.

---

## 5. Agent Tool Selection

The generated tools are exposed to the AI agent.

For example:

```text
Available tools:

list_users()
get_user(id)
create_user(name, email)
delete_user(id)
```

If the user says:

> "Get information about user 42."

The AI can select:

```text
get_user(id=42)
```

---

## 6. Tool Execution

ToolForge contains a generic execution layer that converts the tool invocation into the corresponding API request.

```text
get_user(id=42)
       ↓
GET /users/42
       ↓
API
       ↓
Response
       ↓
Agent
```

This allows the same execution mechanism to work with many different APIs.

---

# 🏗️ Architecture

```text
                         ┌──────────────────────┐
                         │        USER          │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      FRONTEND        │
                         │                      │
                         │ API URL Input        │
                         │ Generated Tools      │
                         │ Agent Interface      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       BACKEND        │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┼────────────────┐
                    │               │                │
                    ▼               ▼                ▼
             ┌────────────┐  ┌─────────────┐  ┌──────────────┐
             │ API Parser │  │ Tool Engine │  │ Agent Engine │
             └─────┬──────┘  └──────┬──────┘  └──────┬───────┘
                   │                │                │
                   ▼                ▼                ▼
             ┌────────────────────────────────────────────┐
             │             Normalized API Spec            │
             └─────────────────────┬──────────────────────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │   Gemini    │
                            │             │
                            │ Understand  │
                            │ + Reason    │
                            │ + Select    │
                            │   tools     │
                            └──────┬──────┘
                                   │
                                   ▼
                           ┌───────────────┐
                           │ Tool Executor │
                           └───────┬───────┘
                                   │
                                   ▼
                              External API
```

---

# 🔄 End-to-End Flow

```text
                API Documentation URL
                         │
                         ▼
                 ┌──────────────┐
                 │ API Ingestion│
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │ API Analyzer │
                 └──────┬───────┘
                        │
                        ▼
              ┌─────────────────────┐
              │ Normalized API Spec │
              └──────────┬──────────┘
                         │
                         ▼
                 ┌──────────────┐
                 │ Tool Generator│
                 └──────┬───────┘
                        │
                        ▼
                 Agent Tool Set
                        │
                        ▼
                  ┌───────────┐
                  │  Gemini   │
                  │   Agent   │
                  └─────┬─────┘
                        │
                        ▼
                 Selected Tool
                        │
                        ▼
                Generic Executor
                        │
                        ▼
                    API Call
                        │
                        ▼
                    API Result
                        │
                        ▼
                      Agent
                        │
                        ▼
                     User
```

---

# 🧩 Core Components

## API Parser

Responsible for understanding the provided API specification.

Responsibilities:

* Fetch API/OpenAPI documents
* Parse endpoints
* Extract HTTP methods
* Extract parameters
* Extract request/response schemas
* Identify authentication information
* Create normalized API representation

---

## Tool Generator

Converts normalized API endpoints into agent-compatible tool definitions.

Example:

```text
Endpoint:

GET /users/{id}

        ↓

Tool:

Name:
get_user

Arguments:
id: integer

Description:
Retrieve a user by ID.
```

---

## Tool Executor

The Tool Executor provides a generic mechanism for executing generated tools.

Instead of manually implementing every endpoint, it interprets the generated tool definition.

Example:

```text
Tool:
get_user

Method:
GET

Path:
 /users/{id}

Arguments:
id = 42
```

The executor constructs:

```text
GET /users/42
```

and performs the request.

---

## Agent Engine

The agent receives:

1. User instructions
2. Available tools
3. Tool schemas/descriptions

Gemini determines which tool should be used and what arguments should be supplied.

Example:

```text
User:
"Find user 42."

Gemini:
Tool → get_user
Arguments → { "id": 42 }
```

---

# 🤖 Role of Gemini

Gemini is used as the intelligence layer of ToolForge.

It can assist with:

### API understanding

Understanding endpoint descriptions, parameters, schemas, and API semantics.

### Tool generation

Converting API capabilities into structured, agent-friendly tool definitions.

### Tool selection

Determining which generated tool best satisfies a user's request.

### Natural-language interaction

Allowing users to interact with APIs without needing to know the underlying API syntax.

The goal is not simply to use an LLM to generate text.

The LLM is used to create a bridge between:

```text
Natural Language
       ↕
Agent Tools
       ↕
API
```

---

# 🛠️ Tech Stack

The exact implementation can evolve during the hackathon, but the MVP is designed around:

### AI

* **Google Gemini Flash models**
* Gemini tool/function-calling capabilities where applicable

### AI Coding

* **LatentCode**
* Used as the project's required AI coding harness

### Frontend

* React
* Modern CSS / UI framework as appropriate

### Backend

* Python / FastAPI

### API Integration

* HTTP client
* OpenAPI parsing
* Dynamic request construction

### Development

* Git
* GitHub
* Environment variables for secrets

### Deployment

A lightweight cloud deployment suitable for the hackathon demo.

---

# 📁 Project Structure

```text
toolforge/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.*
│   └── package.json
│
├── backend/
│   ├── api_parser/
│   │   ├── parser.*
│   │   └── normalizer.*
│   │
│   ├── tool_generator/
│   │   ├── generator.*
│   │   └── schemas.*
│   │
│   ├── tool_executor/
│   │   ├── executor.*
│   │   └── authentication.*
│   │
│   ├── agent/
│   │   ├── agent.*
│   │   └── prompts.*
│   │
│   ├── routes/
│   │   └── api.*
│   │
│   └── main.*
│
├── docs/
│   └── architecture.md
│
├── .env.example
├── .gitignore
├── README.md
└── LICENSE
```

The exact filenames may differ depending on the implementation.

---

# 🔐 Security Considerations

ToolForge is designed with the assumption that API credentials are sensitive.

The MVP should follow basic security practices:

* Never commit API keys to Git
* Store secrets in environment variables
* Never expose server-side secrets to the frontend
* Validate API URLs
* Validate generated tool arguments
* Restrict dangerous operations where appropriate
* Handle API errors safely
* Avoid logging sensitive credentials
* Clearly distinguish between tool generation and tool execution

For production use, additional controls would be required around authentication, authorization, sandboxing, rate limiting, SSRF protection, and user-specific credentials.

---

# ⚠️ Current Scope

ToolForge is a hackathon proof of concept.

The goal is to demonstrate the complete pipeline:

```text
API Specification
      ↓
Understand
      ↓
Generate Tools
      ↓
Agent
      ↓
Execute
      ↓
Real API
```

The initial implementation focuses on APIs with accessible OpenAPI/Swagger specifications.

The architecture is designed to be extended to documentation pages and more complex APIs in the future.

---

# 🧪 Demonstration

The hackathon demonstration focuses on a simple workflow.

### Step 1 — Provide an API

```text
API/OpenAPI URL
```

### Step 2 — Analyze

ToolForge displays:

```text
✓ API detected
✓ Authentication detected
✓ Endpoints discovered
✓ Schemas discovered
```

### Step 3 — Generate tools

Example:

```text
Generated Tools

get_user(id)
list_users()
create_user(name, email)
delete_user(id)
```

### Step 4 — Ask the agent

```text
"Get information about user 42."
```

### Step 5 — Agent invokes the tool

```text
get_user(id=42)
```

### Step 6 — ToolForge executes the API call

```text
GET /users/42
```

### Step 7 — Result is returned

```text
User 42
Name: Rahul
Email: rahul@example.com
```

This demonstrates that the generated tools are not merely static descriptions — they can be connected to an agent execution workflow.

---

# 🌎 Future Vision

ToolForge can evolve beyond OpenAPI-based APIs.

Potential future capabilities include:

### Documentation-to-tool generation

Support APIs where documentation exists only as human-readable webpages.

### More authentication methods

Support:

* OAuth 2.0
* API keys
* Bearer tokens
* Basic authentication
* Custom authentication schemes

### Advanced API behavior

Automatically understand:

* Pagination
* Rate limits
* Retries
* Webhooks
* Nested resources
* API versioning
* Error recovery

### Connector testing

Automatically generate test cases and verify that generated tools behave as expected.

### Tool quality scoring

Before exposing a connector to an agent:

```text
Authentication      ✓
Schema completeness ✓
Parameter validity  ✓
Endpoint reachable  ✓
Response parsing    ✓
```

### Connector marketplace

A future version could allow developers to publish and reuse generated connectors.

### Multi-API agents

An agent could use tools from multiple APIs simultaneously.

For example:

```text
GitHub + Jira + Slack

       ↓

      Agent

       ↓

"Find the GitHub issue,
create a Jira ticket,
and notify the team in Slack."
```

That would turn ToolForge into a general-purpose integration layer for AI agents.

---

# 💭 Why This Matters

The future of AI agents is not just about making models smarter.

Agents need access to the outside world.

They need to:

* read data
* search systems
* create records
* update information
* communicate with services
* trigger workflows
* interact with business systems

APIs are the interface to that world.

ToolForge explores a simple question:

> **What if connecting an AI agent to a new API could be automated?**

Instead of developers manually building every integration, ToolForge aims to make APIs understandable and usable by agents automatically.

---

# 🏆 Built for LatentForce BuildSprint 2026

ToolForge was built as part of **LatentForce BuildSprint**, a 48-hour online hackathon.

### Hackathon

**LatentForce BuildSprint 2026**

### Project

**ToolForge**

### Category

AI Agents / Developer Tools / API Automation

### Core Technologies

* Gemini
* LatentCode
* APIs
* OpenAPI
* Agent Tool Calling

---

# 👥 Team

| Role                   | Responsibility                                    |
| ---------------------- | ------------------------------------------------- |
| API Intelligence       | API ingestion, parsing and normalization          |
| Agent & Runtime        | Tool generation, Gemini integration and execution |
| Frontend & Integration | UI, integration, deployment and presentation      |

---

# 🚀 Quick Start

## Prerequisites

* Node.js
* Python
* API credentials where required
* Gemini API credentials
* Git

## Clone

```bash
git clone <repository-url>
cd toolforge
```

## Configure environment

Create an environment file based on:

```text
.env.example
```

Add the required API credentials.

## Start the backend

```bash
cd backend

# Create & activate virtual environment
# On macOS/Linux:
python3 -m venv venv
source venv/bin/activate

# On Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# Set GEMINI_API_KEY in environment or .env file

# Start the FastAPI server
uvicorn main:app --reload --port 8000
```

## Start the frontend

In a separate terminal window:

```bash
cd frontend

# Install dependencies
npm install

# Configure environment (optional, defaults to http://localhost:8000)
# VITE_API_BASE_URL=http://localhost:8000

# Start development server
npm run dev
```

Then open `http://localhost:5173` in your browser.

---

# 🔮 From APIs to Agent Capabilities

ToolForge is an exploration of a future where APIs don't need to be manually integrated into every AI agent.

```text
                 TODAY

API ─────→ Developer ─────→ Custom Integration ─────→ Agent


                 TOOLFORGE

API Documentation
        │
        ▼
    ToolForge
        │
        ▼
 Agent-ready Tools
        │
        ▼
       Agent
```

**Build once. Adapt automatically. Give agents access to more of the world.**

---

## 📜 License

This project was created as a hackathon project. Add the appropriate license before public release.
