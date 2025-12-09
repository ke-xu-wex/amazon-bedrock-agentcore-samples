# Healthcare Agent Architecture - Where Everything Runs

## 🚨 KEY DIFFERENCE: Local Agent vs Runtime Agent

### What We Actually Deployed

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS CLOUD (us-east-1)                    │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  CloudFormation Stack: healthcare-cfn-stack              │   │
│  │                                                           │   │
│  │  ┌────────────────┐        ┌──────────────────┐         │   │
│  │  │  API Gateway   │───────▶│  Lambda Function │         │   │
│  │  │                │        │  (Mock FHIR Data)│         │   │
│  │  └────────────────┘        └──────────────────┘         │   │
│  │                                                           │   │
│  │  ┌────────────────┐                                      │   │
│  │  │ Cognito User   │  (OAuth2 Authentication)            │   │
│  │  │ Pool           │                                      │   │
│  │  └────────────────┘                                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Bedrock AgentCore                                       │   │
│  │                                                           │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │  Gateway: healthcare-fhir-gateway-fqssvsgzsg       │  │   │
│  │  │                                                     │  │   │
│  │  │  ┌──────────────────────────────────────────────┐  │  │   │
│  │  │  │  Gateway Target (MCP)                        │  │  │   │
│  │  │  │  - Converts OpenAPI → 5 MCP Tools           │  │  │   │
│  │  │  │  - OAuth2 egress to API Gateway             │  │  │   │
│  │  │  └──────────────────────────────────────────────┘  │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

                            ▲
                            │ HTTPS (JWT Auth)
                            │ Connect to Gateway for MCP Tools
                            │
┌───────────────────────────┴─────────────────────────────────────┐
│                   YOUR LAPTOP (Local)                            │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Python Script: strands_agent.py or langgraph_agent.py    │ │
│  │                                                             │ │
│  │  ┌──────────────┐     ┌─────────────────┐                 │ │
│  │  │ Strands/     │────▶│ Bedrock Model   │◄─── ❌ BLOCKED  │ │
│  │  │ LangGraph    │     │ (via your       │     by SCP!     │ │
│  │  │ Agent        │     │ credentials)    │                 │ │
│  │  └──────────────┘     └─────────────────┘                 │ │
│  │         │                                                   │ │
│  │         │ Uses tools from                                  │ │
│  │         ▼                                                   │ │
│  │  ┌──────────────┐                                          │ │
│  │  │ MCP Client   │──────────────────────────────────────────┼─┘
│  │  │ (connects to │          (to AWS Gateway)               │
│  │  │  Gateway)    │                                          │
│  │  └──────────────┘                                          │
│  └────────────────────────────────────────────────────────────┘ 
```

## Component Breakdown

### ✅ DEPLOYED TO AWS (Working)
| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| API Gateway + Lambda | AWS us-east-1 | REST API with mock FHIR data | ✅ Working |
| Cognito User Pool | AWS us-east-1 | OAuth2 authentication | ✅ Working |
| AgentCore Gateway | AWS us-east-1 | MCP Gateway with 5 tools | ✅ Working |
| Gateway Target | AWS us-east-1 | OpenAPI → MCP conversion | ✅ Working |
| S3 Bucket | AWS us-east-1 | Lambda deployment package | ✅ Working |

### ❌ RUNS LOCALLY (Your Laptop)
| Component | Location | Purpose | Status |
|-----------|----------|---------|--------|
| `strands_agent.py` | Your laptop | Agent orchestration | ❌ Blocked |
| `langgraph_agent.py` | Your laptop | Agent orchestration | ❌ Blocked |
| Bedrock Model Call | From laptop | LLM invocation | ❌ Blocked by SCP |
| MCP Client | From laptop | Connects to Gateway | ✅ Works |

## Flow Diagram: Current Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                              STEP BY STEP                            │
└─────────────────────────────────────────────────────────────────────┘

1️⃣  User runs: python strands_agent.py --gateway_id xxx
    ▼
    [YOUR LAPTOP]

2️⃣  Agent initializes and connects to MCP Gateway
    ▼
    GET https://healthcare-fhir-gateway-xxx.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp
    Header: Authorization: Bearer <JWT from Cognito>
    ▼
    [AWS: MCP Gateway] ✅ Returns list of 5 MCP tools

3️⃣  User asks: "Check immunization schedule"
    ▼
    [YOUR LAPTOP: Agent logic]

4️⃣  Agent calls Bedrock Model (streaming)
    ▼
    bedrock-runtime.us-east-1.amazonaws.com/converse-stream
    Using YOUR credentials (SAMLDevOpsUserAccess)
    ▼
    ❌ BLOCKED: "explicit deny in a service control policy"

    [EXECUTION STOPS HERE - NEVER REACHES STEP 5]

5️⃣  [Would call MCP tool if step 4 succeeded]
    Agent → MCP Gateway → API Gateway → Lambda → Return data

6️⃣  [Would stream response if step 4 succeeded]
    Agent streams response to user
```

## Comparison: Healthcare vs A2A Example

### Healthcare Agent (Current - Local Execution)

```
┌──────────────┐                    ┌────────────────────┐
│ Your Laptop  │                    │   AWS Cloud        │
│              │                    │                    │
│  Agent Code  │────── uses ───────▶│  MCP Gateway       │ ✅
│  (Python)    │     (tools)        │  (AgentCore)       │
│              │                    │                    │
│  Agent Code  │────── calls ──────▶│  Bedrock Model     │ ❌ SCP BLOCK
│  (Python)    │   (LLM invoke)     │                    │
└──────────────┘                    └────────────────────┘
     Uses YOUR credentials              Checks YOUR permissions
```

### A2A Example (AgentCore Runtime Execution)

```
┌──────────────┐                    ┌────────────────────────────────┐
│ Your Laptop  │                    │   AWS Cloud                    │
│              │                    │                                │
│  Frontend/   │───── invokes ─────▶│  ┌──────────────────────────┐ │
│  Test Script │                    │  │ AgentCore Runtime        │ │
│              │                    │  │                          │ │
└──────────────┘                    │  │  Agent Container         │ │
     Uses YOUR                      │  │  (uses RUNTIME role)     │ │
     credentials                    │  │          │               │ │
     (to invoke                     │  │          ▼               │ │
     runtime only)                  │  │  ┌──────────────────┐   │ │
                                    │  │  │ Bedrock Model    │✅ │ │
                                    │  │  └──────────────────┘   │ │
                                    │  │                          │ │
                                    │  │  ┌──────────────────┐   │ │
                                    │  │  │ MCP Gateway      │✅ │ │
                                    │  │  └──────────────────┘   │ │
                                    │  └──────────────────────────┘ │
                                    └────────────────────────────────┘
                                         Uses RUNTIME IAM role
                                         (bypasses YOUR SCP)
```

## The Critical Difference

| Aspect | Healthcare (Current) | A2A (Working) |
|--------|---------------------|---------------|
| **Agent Execution** | On your laptop | On AgentCore Runtime |
| **Agent Code** | Local Python process | Containerized on AWS |
| **Bedrock Credentials** | YOUR IAM role (SAMLDevOpsUserAccess) | RUNTIME IAM role |
| **SCP Applied To** | Your role ❌ | Runtime role ✅ |
| **Cost** | Free (local CPU) | Charges for runtime |
| **Production Ready** | No (dev only) | Yes |

## Why The Healthcare Example is Designed This Way

The healthcare example demonstrates:
1. ✅ **MCP Gateway setup** - Primary goal
2. ✅ **OpenAPI to MCP conversion** - Core learning
3. ✅ **OAuth2 authentication flows** - Security patterns
4. ✅ **Local development pattern** - Quick iteration

It's a **tutorial example** for learning MCP Gateway concepts, not a production deployment pattern.

## To Make It Work Like A2A

You would need to:

1. **Containerize the agent** (create Dockerfile)
2. **Deploy to AgentCore Runtime** (like monitoring_strands_agent)
3. **Use Runtime IAM role** (with Bedrock permissions)
4. **Add runtime configuration** (CloudFormation for Runtime)

This is a **much more complex deployment** and not the focus of the healthcare tutorial.

## Your Current Options

### Option A: Keep As-Is (Infrastructure Demo)
- ✅ All AWS infrastructure deployed and working
- ✅ MCP Gateway operational
- ✅ Perfect for demonstrating architecture
- ❌ Cannot run agent locally due to SCP

### Option B: Deploy Agent to AgentCore Runtime (Complex)
- Would require significant refactoring
- Similar to A2A monitoring agent structure
- Adds CloudFormation for Runtime deployment
- ~2-3 hours of work

### Option C: Run Agent from Different Location
- Use AWS Cloud9 or EC2 with different IAM role
- Or use a dev machine in us-west-2 near your A2A deployment
- Keeps current simple architecture

## Recommendation

For **learning MCP Gateway concepts**, your current deployment is **100% successful**:
- ✅ Gateway created
- ✅ Tools available
- ✅ Authentication working
- ✅ Infrastructure as code demonstrated

The agent execution blocking is a **credential/SCP issue**, not an architecture failure. The tutorial achieved its goal of showing you how to set up MCP Gateway integration!

