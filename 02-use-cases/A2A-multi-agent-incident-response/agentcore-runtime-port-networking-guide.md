# AWS BedrockAgentCore Runtime - Port Configuration & Network Routing Guide

## Table of Contents

- [Overview](#overview)
- [Port Conventions by Protocol](#port-conventions-by-protocol)
- [Network Architecture](#network-architecture)
- [Traffic Routing Flow](#traffic-routing-flow)
- [Agent-to-Agent Communication](#agent-to-agent-communication)
- [Port Configuration Details](#port-configuration-details)
- [Code Examples](#code-examples)
- [FAQ](#faq)

---

## Overview

AWS BedrockAgentCore Runtime uses **convention-based port mapping** where the port is automatically determined by the `ProtocolConfiguration` specified in CloudFormation/CDK. There is **no explicit port configuration** - the Runtime knows which port to route to based on the protocol type.

**Key Principle**: Port numbers are **NOT configurable** - they are hardcoded conventions that match the protocol specification.

---

## Port Conventions by Protocol

| Protocol Configuration        | Container Port | Primary Path   | Health Check | Use Case                                 |
| ----------------------------- | -------------- | -------------- | ------------ | ---------------------------------------- |
| `ProtocolConfiguration: HTTP` | **8080**       | `/invocations` | `/ping`      | Traditional agents with HTTP REST API    |
| `ProtocolConfiguration: MCP`  | **8000**       | `/mcp`         | N/A          | Model Context Protocol servers for tools |
| `ProtocolConfiguration: A2A`  | **9000**       | `/invocations` | `/health`    | Agent-to-Agent protocol servers          |

### Documentation References

**HTTP Protocol (Port 8080)**

```properties
# From: 03-integrations/agentic-frameworks/java_adk/src/main/resources/application.properties
# Amazon Bedrock AgentCore Runtime requires port 8080
server.port=8080
```

**MCP Protocol (Port 8000)**

```markdown
From: 01-tutorials/01-AgentCore-runtime/02-hosting-MCP-server/README.md

"Your MCP server will then be hosted on port 8000 and will provide one invocation
path: the mcp-POST. When you set your AgentCore protocol to MCP, AgentCore Runtime
will expect the MCP server container to be on path 0.0.0.0:8000/mcp as that's the
default path supported by most of the official MCP server SDKs."
```

**A2A Protocol (Port 9000)**

```python
# From: monitoring_strands_agent/main.py and web_search_openai_agents/main.py
runtime_url = os.environ.get("AGENTCORE_RUNTIME_URL", "http://127.0.0.1:9000/")
host, port = "0.0.0.0", 9000
```

---

## Network Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Clients                          │
│              (Frontend, CLI, Host Agent, etc.)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTPS (Port 443)
                             │ OAuth 2.0 Bearer Token
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         AWS BedrockAgentCore Runtime Service Endpoint           │
│     https://bedrock-agentcore.{region}.amazonaws.com            │
│                                                                   │
│  Routes:                                                          │
│  /runtimes/{AGENT_ARN}/invocations                              │
│  /runtimes/{AGENT_ARN}/invocations/.well-known/agent-card.json │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Automatic Port Mapping
                             │ Based on ProtocolConfiguration
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  HTTP Agent   │    │  MCP Server   │    │  A2A Agent    │
│  Container    │    │  Container    │    │  Container    │
│               │    │               │    │               │
│  Port: 8080   │    │  Port: 8000   │    │  Port: 9000   │
│  Path: /invo  │    │  Path: /mcp   │    │  Path: /invo  │
└───────────────┘    └───────────────┘    └───────────────┘
```

### A2A Multi-Agent Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                      External User/Frontend                         │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
                              │ HTTPS (443) + Bearer Token
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              AWS AgentCore Runtime - Host Agent                      │
│              https://bedrock-agentcore.us-west-2.amazonaws.com/     │
│              /runtimes/{HOST_AGENT_ARN}/invocations                 │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              │ Routes to Container Port 8080
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Host Agent Container                              │
│                    (Google ADK Agent)                                │
│                    Protocol: HTTP                                    │
│                    Port: 8080 (internal)                             │
│                                                                       │
│  Discovers other agents via:                                         │
│  1. SSM Parameter Store (runtime IDs)                                │
│  2. Constructs Agent ARNs                                            │
│  3. Fetches agent cards                                              │
└──────────────────┬────────────────────────────┬─────────────────────┘
                   │                            │
                   │ M2M OAuth Token            │ M2M OAuth Token
                   │                            │
                   ▼                            ▼
    ┌──────────────────────────────┐  ┌──────────────────────────────┐
    │ Monitoring Agent Runtime     │  │ Web Search Agent Runtime     │
    │ Protocol: A2A                │  │ Protocol: A2A                │
    └──────────────┬───────────────┘  └──────────────┬───────────────┘
                   │                                  │
                   │ Routes to Port 9000              │ Routes to Port 9000
                   ▼                                  ▼
    ┌──────────────────────────────┐  ┌──────────────────────────────┐
    │  Monitoring Agent Container  │  │  Web Search Agent Container  │
    │  (Strands Agents SDK)        │  │  (OpenAI Agents SDK)         │
    │  Port: 9000 (internal)       │  │  Port: 9000 (internal)       │
    │  Path: /invocations          │  │  Path: /invocations          │
    └──────────────────────────────┘  └──────────────────────────────┘
```

---

## Traffic Routing Flow

### 1. External Request to Agent

```
User Request
    │
    ▼
[HTTPS Request to AWS]
https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/
  arn%3Aaws%3Abedrock-agentcore%3Aus-west-2%3A123456789%3Aruntime%2Fmonitor-agent/
  invocations
    │
    │ Headers:
    │ - Authorization: Bearer {jwt_token}
    │ - X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: {session_id}
    │ - X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actorid: {actor_id}
    │
    ▼
[AgentCore Runtime Service]
    │
    │ 1. Validates JWT token
    │ 2. Checks ProtocolConfiguration → "A2A"
    │ 3. Routes to container port 9000
    │
    ▼
[Container: 0.0.0.0:9000]
    │
    ▼
[Agent Application receives request]
```

### 2. Agent-to-Agent Communication (A2A)

```
Host Agent (Port 8080)
    │
    │ 1. Fetch runtime IDs from SSM Parameter Store
    │    - /monitoragent/agentcore/runtime-id
    │    - /monitoragent/agentcore/provider-name
    │
    ▼
[Construct Agent ARN]
arn:aws:bedrock-agentcore:us-west-2:123456789:runtime/monitor-agent-id
    │
    │ 2. Build Agent Card URL
    │
    ▼
https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/
  {escaped_arn}/invocations/.well-known/agent-card.json
    │
    │ 3. Get M2M OAuth Token
    │    @requires_access_token(provider_name, auth_flow="M2M")
    │
    ▼
[Create httpx.AsyncClient with Bearer Token]
    │
    │ Headers:
    │ - Authorization: Bearer {m2m_token}
    │ - X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: {session_id}
    │ - X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actorid: {actor_id}
    │
    ▼
[POST to /invocations]
    │
    ▼
[AgentCore Runtime routes to Monitor Agent port 9000]
    │
    ▼
[Monitor Agent processes request and responds]
```

---

## Agent-to-Agent Communication

### Host Agent Discovery & Connection Code

**Step 1: Agent Discovery via SSM Parameters**

```python
# From: host_adk_agent/agent.py

MONITOR_AGENT_ID = get_ssm_parameter("/monitoragent/agentcore/runtime-id")
MONITOR_PROVIDER_NAME = get_ssm_parameter("/monitoragent/agentcore/provider-name")
MONITOR_AGENT_ARN = (
    f"arn:aws:bedrock-agentcore:{region}:{account_id}:runtime/{MONITOR_AGENT_ID}"
)

WEBSEARCH_AGENT_ID = get_ssm_parameter("/websearchagent/agentcore/runtime-id")
WEBSEARCH_PROVIDER_NAME = get_ssm_parameter("/websearchagent/agentcore/provider-name")
WEBSEARCH_AGENT_ARN = (
    f"arn:aws:bedrock-agentcore:{region}:{account_id}:runtime/{WEBSEARCH_AGENT_ID}"
)
```

**Step 2: Construct Agent Card URLs**

```python
# From: host_adk_agent/agent.py

monitor_agent_card_url = (
    f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/"
    f"{quote(MONITOR_AGENT_ARN, safe='')}/invocations/.well-known/agent-card.json"
)

# Example URL:
# https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/
#   arn%3Aaws%3Abedrock-agentcore%3Aus-west-2%3A123456789%3Aruntime%2Fmonitor-agent/
#   invocations/.well-known/agent-card.json
```

**Step 3: Authentication Setup**

```python
# From: host_adk_agent/agent.py

@requires_access_token(
    provider_name=provider_name,
    scopes=[],
    auth_flow="M2M",              # Machine-to-Machine OAuth flow
    into="bearer_token",
    force_authentication=True,
)
def _create_client(bearer_token: str = str()) -> httpx.AsyncClient:
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
        "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actorid": actor_id,
    }

    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout=300.0),
        headers=headers,
        limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
    )
```

**Step 4: Create Remote A2A Agents**

```python
# From: host_adk_agent/agent.py

monitor_agent = RemoteA2aAgent(
    name="monitor_agent",
    description="Agent that handles monitoring tasks.",
    agent_card=monitor_agent_card_url,
    a2a_client_factory=_create_client_factory(
        provider_name=MONITOR_PROVIDER_NAME,
        session_id=session_id,
        actor_id=actor_id,
    ),
)

# Create root agent with sub-agents
root_agent = Agent(
    model=GOOGLE_MODEL_ID,
    name="root_agent",
    instruction=SYSTEM_PROMPT,
    sub_agents=[monitor_agent, websearch_agent],
)
```

---

## Port Configuration Details

### Where Port 9000 is Configured (A2A Agents)

**1. Monitoring Agent (`monitoring_strands_agent/main.py`)**

```python
# Use the complete runtime URL from environment variable, fallback to local
runtime_url = os.environ.get("AGENTCORE_RUNTIME_URL", "http://127.0.0.1:9000/")
host, port = "0.0.0.0", 9000

# Agent card configuration - runtime_url is used in the agent card
agent_card = AgentCard(
    name="Monitoring Agent",
    description="Monitoring agent that handles CloudWatch logs, metrics...",
    url=runtime_url,  # ← This URL must match the actual port
    # ... other config
)

# Start the server
if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)
```

**2. Web Search Agent (`web_search_openai_agents/main.py`)**

```python
runtime_url = os.getenv("AGENTCORE_RUNTIME_URL", "http://127.0.0.1:9000/")
host, port = "0.0.0.0", 9000

agent_card = AgentCard(
    name="Web Search Agent",
    description="Web search agent for finding AWS solutions...",
    url=runtime_url,
    # ... other config
)

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)
```

**3. Dockerfiles (All Agents)**

```dockerfile
# From: monitoring_strands_agent/Dockerfile
# web_search_openai_agents/Dockerfile
# host_adk_agent/Dockerfile

EXPOSE 9000
EXPOSE 8000
EXPOSE 8080

# Note: Multiple ports are exposed, but the application
# chooses which one to listen on based on protocol
```

### CloudFormation Configuration

**Monitoring Agent (A2A Protocol)**

```yaml
# From: cloudformation/monitoring_agent.yaml
AgentRuntime:
  Type: AWS::BedrockAgentCore::Runtime
  Properties:
    AgentRuntimeArtifact:
      ContainerConfiguration:
        ContainerUri: !Sub "${AWS::AccountId}.dkr.ecr.${AWS::Region}..."
    ProtocolConfiguration: A2A # ← Runtime knows to route to port 9000
    # NO explicit port configuration - it's convention-based!
```

**Host Agent (HTTP Protocol)**

```yaml
# From: cloudformation/host_agent.yaml
AgentRuntime:
  Type: AWS::BedrockAgentCore::Runtime
  Properties:
    AgentRuntimeArtifact:
      ContainerConfiguration:
        ContainerUri: !Sub "${AWS::AccountId}.dkr.ecr.${AWS::Region}..."
    ProtocolConfiguration: HTTP # ← Runtime knows to route to port 8080
```

---

## Code Examples

### Example 1: Running A2A Agent Locally

```python
# monitoring_strands_agent/main.py
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
import uvicorn

# Local development configuration
runtime_url = os.environ.get("AGENTCORE_RUNTIME_URL", "http://127.0.0.1:9000/")
host, port = "0.0.0.0", 9000

# Create A2A server with agent card
server = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)
app = server.build()

# Add custom endpoints
@app.route("/ping", methods=["GET"])
async def ping(request):
    return JSONResponse({"status": "healthy"})

# Start server
if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)
```

**Running locally:**

```bash
cd monitoring_strands_agent
python main.py
# Server starts on http://0.0.0.0:9000
```

### Example 2: Testing Agent Connection

```python
# From: test/connect_agent.py
import httpx
from urllib.parse import quote

# Construct runtime URL
escaped_agent_arn = quote(agent_arn, safe="")
runtime_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{escaped_agent_arn}/invocations"

# Add authentication headers
headers = {
    "Authorization": f"Bearer {bearer_token}",
    "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
    "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actorid": "TestActor",
}

async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, headers=headers) as httpx_client:
    # Get agent card from the runtime URL
    resolver = A2ACardResolver(httpx_client=httpx_client, base_url=runtime_url)
    agent_card = await resolver.get_agent_card()

    # Create client and send message
    config = ClientConfig(httpx_client=httpx_client, streaming=False)
    factory = ClientFactory(config)
    client = factory.create(agent_card)

    msg = create_message(text="What log groups are available?")
    async for response in client.send_message(msg):
        print(response)
```

### Example 3: Port Mismatch Issue

**BROKEN - Port mismatch will cause connection failure:**

```python
# DON'T DO THIS - runtime_url doesn't match actual port
runtime_url = os.environ.get("AGENTCORE_RUNTIME_URL", "http://127.0.0.1:9000/")
host, port = "0.0.0.0", 8000  # ← WRONG! Agent listens on 8000

agent_card = AgentCard(
    url=runtime_url,  # ← Says "I'm on port 9000"
    # ... other config
)

# Agent card says port 9000, but app listens on 8000
# Other agents will try to connect to 9000 and fail!
```

**CORRECT - Both must match:**

```python
# Both runtime_url and port must match
runtime_url = os.environ.get("AGENTCORE_RUNTIME_URL", "http://127.0.0.1:9000/")
host, port = "0.0.0.0", 9000  # ← CORRECT! Matches runtime_url

agent_card = AgentCard(
    url=runtime_url,  # ← Port 9000 in URL
    # ... other config
)

uvicorn.run(app, host=host, port=port)  # ← Listens on port 9000
```

### Example 4: Environment Variable Configuration

```python
# Make port configurable via environment variables
PORT = int(os.environ.get("PORT", "9000"))
runtime_url = os.environ.get("AGENTCORE_RUNTIME_URL", f"http://127.0.0.1:{PORT}/")
host, port = "0.0.0.0", PORT

# Now you can change port via environment variable
# export PORT=9000
# export AGENTCORE_RUNTIME_URL=http://127.0.0.1:9000/
```

---

## FAQ

### Q: Why do all A2A agents use port 9000?

**A:** Port 9000 is the **convention** for A2A protocol servers. When you specify `ProtocolConfiguration: A2A` in CloudFormation, AWS AgentCore Runtime automatically routes traffic to port 9000 inside the container. This is not configurable - it's part of the protocol specification.

### Q: Can I change the port from 9000 to 8000?

**A:** Technically yes in your code, but **not recommended**. If you change the application port without changing the protocol configuration, the AgentCore Runtime will still try to route to port 9000 and fail. The port conventions are:

- A2A → 9000
- MCP → 8000
- HTTP → 8080

### Q: How does AgentCore Runtime know which port to use?

**A:** The Runtime uses **convention-based routing** based on `ProtocolConfiguration`:

- `ProtocolConfiguration: A2A` → Routes to container port 9000
- `ProtocolConfiguration: MCP` → Routes to container port 8000
- `ProtocolConfiguration: HTTP` → Routes to container port 8080

There is **NO port discovery** - it's hardcoded by convention.

### Q: Why can't I specify a custom port in CloudFormation?

**A:** The `ContainerConfiguration` only accepts `ContainerUri` - there's no `ContainerPort` parameter. This is by design to enforce standardization and protocol compliance.

### Q: What if I run agents locally on port 8000 but can't get traffic?

**A:** Check these:

1. **Port mismatch**: Ensure `runtime_url` in agent card matches actual listening port
2. **Protocol convention**: A2A agents should use 9000, not 8000
3. **Local vs Deployed**: When deployed to AgentCore Runtime, external traffic comes through AWS endpoint (port 443), not your application port directly

### Q: Do I expose port 9000 to the internet?

**A:** **NO!** When deployed on AgentCore Runtime:

- External clients connect via `https://bedrock-agentcore.{region}.amazonaws.com` (port 443)
- AgentCore Runtime handles internal routing to container port 9000
- Port 9000 is **internal only** and never exposed publicly
- Port 9000 is only relevant for local development/testing

### Q: How do I test my agent locally before deploying?

**A:**

```bash
# Terminal 1 - Start agent locally
cd monitoring_strands_agent
export AGENTCORE_RUNTIME_URL=http://127.0.0.1:9000/
python main.py

# Terminal 2 - Test with curl
curl http://localhost:9000/health
curl http://localhost:9000/.well-known/agent-card.json
```

### Q: What happens if the agent card URL doesn't match the listening port?

**A:** The agent will start, but other agents/clients won't be able to connect:

- Agent card says: "I'm available at port 9000"
- Agent actually listens on: port 8000
- Result: Connection failures, timeouts, 404 errors

### Q: Can I use environment variables to override the port?

**A:** Yes for local development, but ensure consistency:

```python
PORT = int(os.environ.get("PORT", "9000"))
runtime_url = os.environ.get("AGENTCORE_RUNTIME_URL", f"http://127.0.0.1:{PORT}/")
host, port = "0.0.0.0", PORT
```

But when deployed to AgentCore Runtime, the protocol configuration takes precedence.

---

## Key Takeaways

1. **Port conventions are NOT configurable** - they're determined by `ProtocolConfiguration`
2. **A2A = 9000, MCP = 8000, HTTP = 8080** - memorize these conventions
3. **No port discovery** - AgentCore Runtime uses hardcoded routing based on protocol
4. **Agent card URL must match listening port** - inconsistency causes connection failures
5. **External traffic uses HTTPS (443)** - internal ports are never exposed publicly
6. **Agent-to-Agent uses AWS managed endpoints** - not direct port connections
7. **OAuth 2.0 M2M tokens required** - for agent-to-agent authentication
8. **SSM Parameter Store** - used for agent discovery (runtime IDs, provider names)

---

## Additional Resources

- [A2A Protocol Specification](https://a2a-protocol.org/latest/)
- [AWS BedrockAgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)

---

_Generated from conversation thread discussing AgentCore Runtime port configuration and networking_
_Date: December 5, 2025_
