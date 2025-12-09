# Customer Support VPC - Quick Networking Reference

## TL;DR - The Networking Essentials

**What**: Fully private VPC deployment of Bedrock AgentCore with zero internet access

**How**: 13 VPC endpoints enable private access to all AWS services

**Why**: Maximum security, compliance-ready, complete network isolation

---

## Key Networking Facts

| Aspect              | Details                                                       |
| ------------------- | ------------------------------------------------------------- |
| **VPC CIDR**        | 10.0.0.0/16 (65,536 IPs)                                      |
| **Subnets**         | 3 private subnets across 3 AZs                                |
| **Internet Access** | NONE (no IGW, no NAT)                                         |
| **VPC Endpoints**   | 13 total (11 interface + 2 gateway)                           |
| **Security Groups** | 4 (VPC Endpoints, MCP Runtime, Agent Runtime, Gateway Lambda) |
| **Route Tables**    | 1 private route table                                         |
| **Cost**            | ~$265/month for VPC endpoints                                 |
| **Deployment Time** | 30-45 minutes                                                 |

---

## The Three Network Layers

### Layer 1: VPC Foundation

```
VPC (10.0.0.0/16)
├── PrivateSubnet1 (10.0.3.0/24) - Agent Runtime
├── PrivateSubnet2 (10.0.4.0/24) - Aurora, Gateway Lambda
└── PrivateSubnet3 (10.0.1.0/24) - MCP Runtime
```

### Layer 2: VPC Endpoints

```
Interface Endpoints (create ENIs):
├── bedrock-runtime, bedrock-agentcore, bedrock-agentcore.gateway
├── ecr.api, ecr.dkr
├── logs, monitoring, xray
├── secretsmanager, ssm, kms
└── rds-data

Gateway Endpoints (route table entries):
├── dynamodb (FREE)
└── s3 (FREE)
```

### Layer 3: Security Groups

```
VPCEndpointSecurityGroup: Allow 10.0.0.0/16 → TCP/443
MCPRuntimeSecurityGroup: Allow Self → VPC Endpoints + DynamoDB
AgentRuntimeSecurityGroup: Allow Self → VPC Endpoints
GatewayLambdaSecurityGroup: Allow Self → VPC Endpoints + DynamoDB
```

---

## Critical Networking Concepts

### 1. VPC Endpoints Enable Everything

**Without VPC Endpoints**:

```
Runtime Container → Public AWS Service ✗ (no internet access)
```

**With VPC Endpoints**:

```
Runtime Container → VPC Endpoint ENI → AWS PrivateLink → AWS Service ✓
```

### 2. Interface vs Gateway Endpoints

| Feature            | Interface            | Gateway              |
| ------------------ | -------------------- | -------------------- |
| **Creates ENIs**   | Yes (one per subnet) | No                   |
| **Cost**           | $0.01/hour per AZ    | FREE                 |
| **Supports**       | Most AWS services    | S3, DynamoDB only    |
| **Private DNS**    | Yes                  | No (uses public IPs) |
| **Security Group** | Required             | Uses route table     |

### 3. Security Group Traffic Flow

```
Source SG          →  Destination SG         Port
──────────────────────────────────────────────────
MCPRuntime         →  VPCEndpoint            443
MCPRuntime         →  DynamoDB Prefix List   443
AgentRuntime       →  VPCEndpoint            443
GatewayLambda      →  VPCEndpoint            443
GatewayLambda      →  DynamoDB Prefix List   443
10.0.0.0/16        →  VPCEndpoint            443
```

### 4. DynamoDB Gateway Endpoint

**How it works**:

1. Container queries `dynamodb.us-west-2.amazonaws.com`
2. DNS returns public IP (e.g., `52.94.x.x`)
3. Traffic hits route table
4. Route table has prefix list entry: `pl-xxxxx → Gateway Endpoint`
5. Traffic redirected to DynamoDB via AWS PrivateLink
6. **Cost**: FREE (no hourly charge, no data processing charge)

### 5. DNS Resolution

**Critical Requirements**:

```yaml
VPC:
  EnableDnsSupport: true # Must be enabled
  EnableDnsHostnames: true # Must be enabled

InterfaceEndpoint:
  PrivateDnsEnabled: true # Creates private Route53 records
```

**What happens**:

```
Container queries: bedrock-runtime.us-west-2.amazonaws.com
DNS resolves to:   10.0.3.100 (VPC endpoint private IP)
NOT:               AWS public IP
```

---

## Common Network Flows

### Flow 1: Agent Calls Bedrock Model

```
Agent Container (10.0.3.x)
  ↓ DNS query
bedrock-runtime.us-west-2.amazonaws.com → 10.0.3.100
  ↓ TCP/443
VPC Endpoint ENI (10.0.3.100)
  ↓ AWS PrivateLink
Bedrock Service
  ↓ Response
Agent Container
```

### Flow 2: MCP Queries DynamoDB

```
MCP Container (10.0.1.x)
  ↓ DNS query
dynamodb.us-west-2.amazonaws.com → 52.94.x.x (public IP)
  ↓ TCP/443
Route Table: prefix list pl-xxxxx → Gateway Endpoint
  ↓ AWS PrivateLink
DynamoDB Service
  ↓ Response
MCP Container
```

### Flow 3: Agent Queries Aurora

```
Agent Container (10.0.3.x)
  ↓ Get credentials
Secrets Manager VPC Endpoint
  ↓ Decrypt
KMS VPC Endpoint
  ↓ Execute SQL
RDS Data API VPC Endpoint
  ↓ Query
Aurora Cluster (10.0.4.x)
  ↓ Results
Agent Container
```

### Flow 4: Container Pulls from ECR

```
Runtime (cold start)
  ↓ Get auth token
ECR API VPC Endpoint (ecr.api)
  ↓ Get manifest
ECR Docker VPC Endpoint (ecr.dkr)
  ↓ Get layers
S3 Gateway Endpoint
  ↓ Download
Container Image Loaded
```

---

## Troubleshooting Checklist

### Issue: Container fails to start

✓ Check ECR endpoints exist (ecr.api, ecr.dkr)  
✓ Verify S3 gateway endpoint configured  
✓ Check security group allows outbound TCP/443  
✓ Confirm IAM role has ECR permissions

### Issue: Agent cannot call Bedrock

✓ Check bedrock-runtime endpoint exists  
✓ Verify DNS resolution enabled on VPC  
✓ Check security group allows outbound TCP/443 to VPC endpoint SG  
✓ Confirm IAM role has bedrock:InvokeModel permission

### Issue: MCP cannot access DynamoDB

✓ Check DynamoDB gateway endpoint exists  
✓ Verify prefix list in security group egress rules  
✓ Check route table has gateway endpoint route  
✓ Confirm IAM role has DynamoDB permissions

### Issue: Logs not appearing

✓ Check logs VPC endpoint exists  
✓ Verify private DNS enabled  
✓ Check IAM role has logs:PutLogEvents permission  
✓ Verify log group exists

---

## Security Best Practices Checklist

✓ **No Internet Gateway**: Ensures no direct internet access  
✓ **No NAT Gateway**: Prevents outbound internet connections  
✓ **Private Subnets Only**: No public IP assignments  
✓ **VPC Endpoints**: Private AWS service access  
✓ **Security Groups**: Least privilege access control  
✓ **VPC Flow Logs**: Network traffic monitoring  
✓ **KMS Encryption**: Data encrypted at rest  
✓ **TLS 1.2+**: Data encrypted in transit  
✓ **IAM Roles**: No hardcoded credentials  
✓ **Secrets Manager**: Centralized secret storage

---

## Cost Optimization Tips

### Current Setup (3 AZs)

```
12 interface endpoints × 3 AZs × $0.01/hr × 730 hr = $262.80/month
2 gateway endpoints = $0/month
Total: ~$265/month
```

### Optimization 1: Reduce to 2 AZs

```
12 interface endpoints × 2 AZs × $0.01/hr × 730 hr = $175.20/month
Savings: $87.60/month (33% reduction)
Trade-off: Lower availability
```

### Optimization 2: Single Subnet Deployment

```
Deploy all runtimes in one subnet
Still need endpoints in multiple subnets for HA
Savings: Minimal (endpoints still needed)
```

### Optimization 3: Share VPC Across Workloads

```
Deploy multiple applications in same VPC
Endpoints shared across all applications
Per-workload cost reduces significantly
```

---

## Key Takeaways

1. **VPC Endpoints Are Essential**: Without them, nothing works in a private VPC
2. **Gateway Endpoints Are Free**: Use for DynamoDB and S3
3. **Security Groups Control Everything**: Properly configure ingress/egress
4. **DNS Must Be Enabled**: Required for endpoint private DNS
5. **ENIs Take 8 Hours to Delete**: Plan cleanup accordingly
6. **Cost is ~$265/month**: For complete VPC endpoint setup
7. **Interface Endpoints = ENIs**: One per subnet per endpoint
8. **Prefix Lists for DynamoDB**: Required for security group rules
9. **No Internet = Maximum Security**: Complete isolation
10. **Production-Ready**: Meets compliance requirements

---

## Quick Commands

### Check VPC Endpoints

```bash
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=vpc-xxx" \
  --query 'VpcEndpoints[*].[ServiceName,State]' \
  --output table
```

### Check Security Groups

```bash
aws ec2 describe-security-groups \
  --group-ids sg-xxx \
  --query 'SecurityGroups[*].{Ingress:IpPermissions,Egress:IpPermissionsEgress}'
```

### Check Route Tables

```bash
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=vpc-xxx" \
  --query 'RouteTables[*].Routes'
```

### View VPC Flow Logs

```bash
aws logs filter-log-events \
  --log-group-name /aws/vpc/flow-logs \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --limit 20
```

### Get DynamoDB Prefix List

```bash
aws ec2 describe-prefix-lists \
  --filters "Name=prefix-list-name,Values=com.amazonaws.us-west-2.dynamodb" \
  --query 'PrefixLists[*].[PrefixListId,PrefixListName]'
```

---

## When to Use This Architecture

### ✅ Perfect For:

- Regulated industries (healthcare, finance, government)
- Compliance requirements (HIPAA, PCI-DSS, FedRAMP)
- Sensitive data processing (PII, PHI)
- Zero-trust security model
- Hybrid cloud with Direct Connect/VPN

### ❌ Not Ideal For:

- Public-facing APIs
- Development/testing environments
- Internet-dependent workloads
- Cost-sensitive projects
- Quick prototypes

---

## Architecture in One Sentence

**A fully isolated VPC with 13 VPC endpoints that enable private access to all AWS services needed by Bedrock AgentCore, with zero internet connectivity and complete security isolation.**

---

## Resources

- Main Analysis: `/ai_tmp/customer-support-vpc-networking-analysis.md`
- Visual Diagram: `/ai_tmp/vpc-network-diagram.md`
- Example Code: `/02-use-cases/customer-support-assistant-vpc/`
- VPC Stack: `/cloudformation/vpc-stack.yaml`
- Deploy Script: `/deploy.sh`
- Cleanup Script: `/cleanup.sh`

