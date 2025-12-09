# Customer Support VPC - Network Topology Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AWS Cloud (us-west-2)                             │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                      VPC (10.0.0.0/16)                                │ │
│  │                                                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │  Availability Zone A (us-west-2a)                            │   │ │
│  │  │                                                              │   │ │
│  │  │  ┌─────────────────────────────────────────────────────┐    │   │ │
│  │  │  │  PrivateSubnet1 (10.0.3.0/24)                       │    │   │ │
│  │  │  │                                                      │    │   │ │
│  │  │  │  ┌────────────────────────────────┐                 │    │   │ │
│  │  │  │  │   Agent Runtime Container      │                 │    │   │ │
│  │  │  │  │   (AgentRuntimeSecurityGroup)  │                 │    │   │ │
│  │  │  │  │   - Bedrock Model Calls        │                 │    │   │ │
│  │  │  │  │   - MCP/Gateway Integration    │                 │    │   │ │
│  │  │  │  │   - Aurora Data API            │                 │    │   │ │
│  │  │  │  └────────────────────────────────┘                 │    │   │ │
│  │  │  │                                                      │    │   │ │
│  │  │  │  ┌──────────────────┐  ┌──────────────────┐        │    │   │ │
│  │  │  │  │ ECR API Endpoint │  │  Logs Endpoint   │        │    │   │ │
│  │  │  │  │   (ENI: 10.0.3.x)│  │  (ENI: 10.0.3.y) │        │    │   │ │
│  │  │  │  └──────────────────┘  └──────────────────┘        │    │   │ │
│  │  │  │                                                      │    │   │ │
│  │  │  └─────────────────────────────────────────────────────┘    │   │ │
│  │  │                                                              │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  │                                                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │  Availability Zone B (us-west-2b)                            │   │ │
│  │  │                                                              │   │ │
│  │  │  ┌─────────────────────────────────────────────────────┐    │   │ │
│  │  │  │  PrivateSubnet2 (10.0.4.0/24)                       │    │   │ │
│  │  │  │                                                      │    │   │ │
│  │  │  │  ┌──────────────────────────────────┐               │    │   │ │
│  │  │  │  │  Aurora PostgreSQL Cluster       │               │    │   │ │
│  │  │  │  │  (Aurora Security Group)         │               │    │   │ │
│  │  │  │  │  - Data API Enabled              │               │    │   │ │
│  │  │  │  │  - Private access only           │               │    │   │ │
│  │  │  │  └──────────────────────────────────┘               │    │   │ │
│  │  │  │                                                      │    │   │ │
│  │  │  │  ┌──────────────────────────────────┐               │    │   │ │
│  │  │  │  │  Gateway Lambda Functions        │               │    │   │ │
│  │  │  │  │  (GatewayLambdaSecurityGroup)    │               │    │   │ │
│  │  │  │  │  - Warranty lookup               │               │    │   │ │
│  │  │  │  │  - Profile management            │               │    │   │ │
│  │  │  │  └──────────────────────────────────┘               │    │   │ │
│  │  │  │                                                      │    │   │ │
│  │  │  │  ┌──────────────────┐  ┌──────────────────┐        │    │   │ │
│  │  │  │  │RDS Data Endpoint │  │Secrets Mgr Endpt │        │    │   │ │
│  │  │  │  │  (ENI: 10.0.4.x) │  │ (ENI: 10.0.4.y)  │        │    │   │ │
│  │  │  │  └──────────────────┘  └──────────────────┘        │    │   │ │
│  │  │  │                                                      │    │   │ │
│  │  │  └─────────────────────────────────────────────────────┘    │   │ │
│  │  │                                                              │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  │                                                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │  Availability Zone C (us-west-2c)                            │   │ │
│  │  │                                                              │   │ │
│  │  │  ┌─────────────────────────────────────────────────────┐    │   │ │
│  │  │  │  PrivateSubnet3 (10.0.1.0/24)                       │    │   │ │
│  │  │  │                                                      │    │   │ │
│  │  │  │  ┌────────────────────────────────┐                 │    │   │ │
│  │  │  │  │   MCP Runtime Container        │                 │    │   │ │
│  │  │  │  │   (MCPRuntimeSecurityGroup)    │                 │    │   │ │
│  │  │  │  │   - DynamoDB Operations        │                 │    │   │ │
│  │  │  │  │   - Reviews & Products Tables  │                 │    │   │ │
│  │  │  │  └────────────────────────────────┘                 │    │   │ │
│  │  │  │                                                      │    │   │ │
│  │  │  │  ┌──────────────────┐  ┌──────────────────┐        │    │   │ │
│  │  │  │  │ KMS Endpoint     │  │ X-Ray Endpoint   │        │    │   │ │
│  │  │  │  │  (ENI: 10.0.1.x) │  │  (ENI: 10.0.1.y) │        │    │   │ │
│  │  │  │  └──────────────────┘  └──────────────────┘        │    │   │ │
│  │  │  │                                                      │    │   │ │
│  │  │  └─────────────────────────────────────────────────────┘    │   │ │
│  │  │                                                              │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  │                                                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │  Private Route Table                                         │   │ │
│  │  │  ┌─────────────────────────────────────────────────────┐    │   │ │
│  │  │  │  Routes:                                             │    │   │ │
│  │  │  │  - 10.0.0.0/16 → local                              │    │   │ │
│  │  │  │  - pl-xxxxx (DynamoDB) → Gateway Endpoint           │    │   │ │
│  │  │  │  - pl-yyyyy (S3) → Gateway Endpoint                 │    │   │ │
│  │  │  └─────────────────────────────────────────────────────┘    │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  │                                                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │  VPC Endpoints (Interface Type - in all 3 subnets)           │   │ │
│  │  │  ┌────────────────────────────────────────────────────────┐  │   │ │
│  │  │  │  • bedrock-runtime (LLM inference)                     │  │   │ │
│  │  │  │  • bedrock-agentcore (runtime management)             │  │   │ │
│  │  │  │  • bedrock-agentcore.gateway (gateway service)        │  │   │ │
│  │  │  │  • ecr.api (ECR authentication)                       │  │   │ │
│  │  │  │  • ecr.dkr (Docker image pull)                        │  │   │ │
│  │  │  │  • logs (CloudWatch Logs)                             │  │   │ │
│  │  │  │  • monitoring (CloudWatch Metrics)                    │  │   │ │
│  │  │  │  • secretsmanager (secrets retrieval)                 │  │   │ │
│  │  │  │  • ssm (Parameter Store)                              │  │   │ │
│  │  │  │  • rds-data (Aurora Data API)                         │  │   │ │
│  │  │  │  • kms (encryption/decryption)                        │  │   │ │
│  │  │  │  • xray (distributed tracing)                         │  │   │ │
│  │  │  │                                                        │  │   │ │
│  │  │  │  Security Group: VPCEndpointSecurityGroup            │  │   │ │
│  │  │  │  Ingress: TCP/443 from 10.0.0.0/16                   │  │   │ │
│  │  │  └────────────────────────────────────────────────────────┘  │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  │                                                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │  VPC Endpoints (Gateway Type - route table entries)          │   │ │
│  │  │  ┌────────────────────────────────────────────────────────┐  │   │ │
│  │  │  │  • dynamodb (DynamoDB service access - FREE)           │  │   │ │
│  │  │  │  • s3 (S3 service access - FREE)                       │  │   │ │
│  │  │  └────────────────────────────────────────────────────────┘  │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  │                                                                       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  AWS Managed Services (outside VPC)                                  │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐                │ │
│  │  │  DynamoDB   │  │  Amazon S3  │  │   Cognito    │                │ │
│  │  │  (via VPC   │  │  (via VPC   │  │  User Pool   │                │ │
│  │  │   endpoint) │  │   endpoint) │  │  (OAuth2)    │                │ │
│  │  └─────────────┘  └─────────────┘  └──────────────┘                │ │
│  │                                                                       │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐                │ │
│  │  │   Bedrock   │  │    ECR      │  │  Secrets     │                │ │
│  │  │   Models    │  │  Registry   │  │   Manager    │                │ │
│  │  │  (Claude)   │  │             │  │              │                │ │
│  │  └─────────────┘  └─────────────┘  └──────────────┘                │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │   Internet   │
                              │              │
                              └──────────────┘
                                      ↑
                                      │ NO CONNECTION
                                      ✗
```

## Security Group Flow Matrix

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Security Group Rules                             │
└─────────────────────────────────────────────────────────────────────────┘

Source                      → Destination                   Port   Protocol
────────────────────────────────────────────────────────────────────────────

VPCEndpointSecurityGroup:
  10.0.0.0/16              → Self                           443    TCP
  (allows all VPC traffic to reach VPC endpoints)

MCPRuntimeSecurityGroup:
  Self                     → VPCEndpointSecurityGroup       443    TCP
  Self                     → DynamoDB Prefix List           443    TCP
  (MCP can access AWS services and DynamoDB)

AgentRuntimeSecurityGroup:
  Self                     → VPCEndpointSecurityGroup       443    TCP
  (Agent can access AWS services including Bedrock, RDS Data API)

GatewayLambdaSecurityGroup:
  Self                     → VPCEndpointSecurityGroup       443    TCP
  Self                     → DynamoDB Prefix List           443    TCP
  (Gateway Lambda can access AWS services and DynamoDB)

NO INBOUND RULES FOR RUNTIMES (all access via Bedrock service endpoints)
```

## Data Flow: End-to-End Request

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Example Request Flow                                 │
│              "Show me products with reviews"                            │
└─────────────────────────────────────────────────────────────────────────┘

1. Client (External)
   ↓ HTTPS
   │
2. Bedrock AgentCore Agent Runtime Public Endpoint
   │ (authenticated via Cognito JWT)
   ↓ Internal Bedrock network
   │
3. Agent Runtime Container (PrivateSubnet1: 10.0.3.x)
   │
   ├─→ bedrock-runtime VPC endpoint (10.0.3.y)
   │   ↓
   │   AWS Bedrock Service
   │   ↓
   │   Claude Model generates response
   │   ↓ "I'll fetch products and their reviews"
   │
   ├─→ bedrock-agentcore VPC endpoint (10.0.3.z)
   │   ↓
   │   Bedrock AgentCore Service
   │   ↓
   │   Routes to MCP Runtime
   │   ↓
   │   MCP Runtime Container (PrivateSubnet3: 10.0.1.x)
   │   │
   │   ├─→ DynamoDB Gateway Endpoint (route table)
   │   │   ↓
   │   │   DynamoDB Service
   │   │   ↓
   │   │   Query Products table
   │   │   Query Reviews table
   │   │   ↓
   │   │   Return: [{product_id: 1, name: "Laptop Pro"}, ...]
   │   │
   │   └─→ logs VPC endpoint (10.0.1.y)
   │       ↓
   │       CloudWatch Logs
   │       ↓
   │       Store MCP execution logs
   │
4. Agent Runtime processes results
   ↓
   │
5. Agent Runtime → bedrock-runtime VPC endpoint
   ↓
   Claude Model formats final response
   ↓
   │
6. Return to client
   ↓
   JSON response with products and reviews
```

## Network Communication Patterns

### Pattern 1: Container Image Pull (ECR)

```
Agent/MCP Runtime (cold start)
  ↓
1. ECR API Endpoint (ecr.api)
   GET /authorization-token
   ← Authorization token
  ↓
2. ECR Docker Endpoint (ecr.dkr)
   GET /v2/{repository}/manifests/{tag}
   ← Image manifest
  ↓
3. S3 Gateway Endpoint
   GET /layer-blobs/{digest}
   ← Container image layers
  ↓
Container started with image
```

### Pattern 2: Aurora Database Query (Data API)

```
Agent Runtime
  ↓
1. Secrets Manager VPC Endpoint
   GET /secrets/{aurora-credentials}
   ← Database credentials (encrypted)
  ↓
2. KMS VPC Endpoint
   POST /decrypt
   ← Decrypted credentials
  ↓
3. RDS Data API VPC Endpoint
   POST /execute-statement
   {
     resourceArn: "arn:aws:rds:...",
     secretArn: "arn:aws:secretsmanager:...",
     database: "sampledb",
     sql: "SELECT * FROM users WHERE customer_id = :id"
   }
   ← Query results
  ↓
4. CloudWatch Logs VPC Endpoint
   POST /log-events
   ← Log stored
```

### Pattern 3: OAuth2 Authentication Flow

```
Agent Runtime (startup)
  ↓
1. Bedrock AgentCore Workload Identity
   GET /workload-identity-token
   ← Workload identity token
  ↓
2. Cognito Token Endpoint (via internet or cached)
   POST /oauth2/token
   grant_type: client_credentials
   client_id: <from secrets>
   client_secret: <from secrets>
   ← OAuth2 access token (JWT)
  ↓
3. Store token in memory
   (used for subsequent MCP/Gateway calls)
  ↓
4. Call MCP/Gateway with token
   Authorization: Bearer <token>
   ↓
5. MCP/Gateway validates JWT
   - Verify signature using Cognito JWKS
   - Check expiration
   - Validate audience/issuer
   ← If valid, process request
```

## VPC Endpoint Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Interface VPC Endpoint (example: logs)               │
└─────────────────────────────────────────────────────────────────────────┘

Outside VPC                     VPC Boundary              Inside VPC
─────────────────               ──────────────            ──────────────

AWS CloudWatch              ←→  VPC Endpoint ENIs    ←→  Runtime Container
Logs Service                    (in each subnet)         (10.0.3.x)

us-west-2.logs.amazonaws.com    PrivateSubnet1:         logs VPC endpoint
(public service)                10.0.3.100              resolved via DNS
                                                        to 10.0.3.100
                                PrivateSubnet2:
                                10.0.4.100              Private DNS enabled:
                                                        logs.us-west-2.amazonaws.com
                                PrivateSubnet3:           → 10.0.3.100
                                10.0.1.100

                                Security Group:
                                VPCEndpointSecurityGroup
                                Allow TCP/443 from 10.0.0.0/16

Traffic Flow:
Container → DNS query for logs.us-west-2.amazonaws.com
         → Route 53 returns 10.0.3.100 (private IP)
         → TCP/443 to 10.0.3.100
         → Security group allows (source: 10.0.0.0/16)
         → ENI forwards to AWS PrivateLink
         → AWS CloudWatch Logs service
         → Response path reverses
```

```
┌─────────────────────────────────────────────────────────────────────────┐
│                 Gateway VPC Endpoint (example: DynamoDB)                │
└─────────────────────────────────────────────────────────────────────────┘

Outside VPC                     VPC Boundary              Inside VPC
─────────────────               ──────────────            ──────────────

Amazon DynamoDB              ←→  Route Table Entries  ←→  MCP Container
Service                          (prefix list)           (10.0.1.x)

dynamodb.us-west-2.amazonaws.com Private Route Table:    dynamodb VPC endpoint
(public service)                                         resolved via DNS
                                Destination: pl-xxxxx    to public IP
                                Target: Gateway Endpoint
                                                        DynamoDB Prefix List:
                                                        52.94.0.0/16
                                                        54.239.0.0/16
                                                        (AWS managed)

Traffic Flow:
Container → DNS query for dynamodb.us-west-2.amazonaws.com
         → Route 53 returns public IP (e.g., 52.94.x.x)
         → TCP/443 to 52.94.x.x
         → Route table matches prefix list
         → Traffic redirected to Gateway Endpoint
         → AWS PrivateLink to DynamoDB
         → Response path reverses

NO ENIs created (just route table entries)
NO hourly charges (free!)
```

## Cost Breakdown per Month (us-west-2)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         VPC Endpoint Costs                              │
└─────────────────────────────────────────────────────────────────────────┘

Interface Endpoints (hourly charge):
─────────────────────────────────
• bedrock-runtime        3 AZ × $0.01/hr × 730 hr = $21.90
• bedrock-agentcore      3 AZ × $0.01/hr × 730 hr = $21.90
• bedrock-agentcore.gw   3 AZ × $0.01/hr × 730 hr = $21.90
• ecr.api                3 AZ × $0.01/hr × 730 hr = $21.90
• ecr.dkr                3 AZ × $0.01/hr × 730 hr = $21.90
• logs                   3 AZ × $0.01/hr × 730 hr = $21.90
• monitoring             3 AZ × $0.01/hr × 730 hr = $21.90
• secretsmanager         3 AZ × $0.01/hr × 730 hr = $21.90
• ssm                    3 AZ × $0.01/hr × 730 hr = $21.90
• rds-data               3 AZ × $0.01/hr × 730 hr = $21.90
• kms                    3 AZ × $0.01/hr × 730 hr = $21.90
• xray                   3 AZ × $0.01/hr × 730 hr = $21.90
                                                    ────────
                                         Subtotal: $262.80

Gateway Endpoints:
──────────────────
• dynamodb               FREE (no hourly charge)
• s3                     FREE (no hourly charge)

Data Processing (estimated):
────────────────────────────
• Interface endpoints    $0.01 per GB processed
• Gateway endpoints      FREE (no data processing charge)

Example: 100 GB/month through interface endpoints = $1.00
         1 TB/month through gateway endpoints = $0.00

Total Estimated VPC Endpoint Cost: ~$265/month
(plus data processing charges)
```

---

## Summary

This VPC architecture provides:

1. **Complete Network Isolation**: No internet gateway, no NAT gateway
2. **Private AWS Service Access**: 13 VPC endpoints for all required services
3. **Multi-AZ High Availability**: Resources spread across 3 availability zones
4. **Layered Security**: VPC isolation + Security Groups + IAM roles
5. **Full Observability**: VPC Flow Logs, CloudWatch, X-Ray tracing
6. **Cost-Optimized**: Gateway endpoints for DynamoDB and S3 (free)
7. **Compliance-Ready**: Meets requirements for HIPAA, PCI-DSS, FedRAMP

The networking design enables Bedrock AgentCore to run in a completely private environment while maintaining full functionality through strategic use of VPC endpoints.

