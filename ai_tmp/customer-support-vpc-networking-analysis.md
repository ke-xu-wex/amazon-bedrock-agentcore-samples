# Customer Support Assistant VPC - Networking Architecture Analysis

## Overview

This example demonstrates a **fully private VPC deployment** of Amazon Bedrock AgentCore without any internet connectivity. All AWS service access is achieved through VPC endpoints, creating a secure, isolated environment for AI workloads.

---

## Network Architecture Components

### 1. VPC Foundation (`vpc-stack.yaml`)

#### VPC Configuration

- **CIDR Block**: `10.0.0.0/16` (65,536 IP addresses)
- **DNS Support**: Enabled (required for VPC endpoints)
- **DNS Hostnames**: Enabled (required for private DNS resolution)

#### Subnets

The architecture uses **3 private subnets** across **3 availability zones** for high availability:

| Subnet         | CIDR        | Availability Zone | Purpose           |
| -------------- | ----------- | ----------------- | ----------------- |
| PrivateSubnet1 | 10.0.3.0/24 | AZ-1              | Agent Runtime     |
| PrivateSubnet2 | 10.0.4.0/24 | AZ-2              | Aurora, Resources |
| PrivateSubnet3 | 10.0.1.0/24 | AZ-3              | MCP Runtime       |

**Key Point**: No public subnets, no Internet Gateway, no NAT Gateway - completely isolated!

#### Routing

- **Single Private Route Table**: Associated with all 3 subnets
- **No Internet Routes**: Only local VPC routes
- **Gateway Endpoints**: Automatically add routes for S3 and DynamoDB

---

## 2. VPC Endpoints - AWS Service Access

The architecture uses **13 VPC endpoints** to enable private communication with AWS services:

### Interface Endpoints (11)

Interface endpoints create ENIs (Elastic Network Interfaces) in each subnet with private IP addresses:

| Service                       | Endpoint Type | Port | Purpose                       |
| ----------------------------- | ------------- | ---- | ----------------------------- |
| **bedrock-runtime**           | Interface     | 443  | LLM inference (Claude models) |
| **bedrock-agentcore**         | Interface     | 443  | AgentCore runtime management  |
| **bedrock-agentcore.gateway** | Interface     | 443  | Gateway service communication |
| **ecr.api**                   | Interface     | 443  | ECR API operations            |
| **ecr.dkr**                   | Interface     | 443  | Docker image pull             |
| **logs**                      | Interface     | 443  | CloudWatch Logs               |
| **monitoring**                | Interface     | 443  | CloudWatch Metrics            |
| **secretsmanager**            | Interface     | 443  | Secrets retrieval             |
| **ssm**                       | Interface     | 443  | Parameter Store               |
| **rds-data**                  | Interface     | 443  | Aurora Data API               |
| **kms**                       | Interface     | 443  | Encryption/Decryption         |
| **xray**                      | Interface     | 443  | Distributed tracing           |

**Configuration Details**:

```yaml
PrivateDnsEnabled: true # Creates private DNS records
SubnetIds: # Deploy in all subnets for HA
  - PrivateSubnet1
  - PrivateSubnet2
  - PrivateSubnet3
SecurityGroupIds:
  - VPCEndpointSecurityGroup # Shared security group
```

### Gateway Endpoints (2)

Gateway endpoints are route table entries (no ENIs):

| Service      | Type    | Purpose                              |
| ------------ | ------- | ------------------------------------ |
| **dynamodb** | Gateway | DynamoDB access via AWS network      |
| **s3**       | Gateway | S3 access (CloudFormation responses) |

**Key Difference**:

- Gateway endpoints are free and scale automatically
- Interface endpoints cost ~$7.20/month per endpoint per AZ

---

## 3. Security Groups - Traffic Control

### VPCEndpointSecurityGroup

Controls access to all interface VPC endpoints:

```yaml
Ingress:
  - Protocol: TCP
    Port: 443
    Source: 10.0.0.0/16 # Allow from entire VPC

Egress:
  - Protocol: TCP
    Port: 443
    Destination: 127.0.0.1/32 # Explicit deny (endpoints don't initiate)
```

**Purpose**: Allows any resource in the VPC to reach AWS services via endpoints.

### MCPRuntimeSecurityGroup

Controls MCP Runtime container networking:

```yaml
Ingress: [] # No inbound - MCP is called by Agent via Bedrock service

Egress:
  - Protocol: TCP
    Port: 443
    Destination: VPCEndpointSecurityGroup # Access to AWS services
  - Protocol: TCP
    Port: 443
    Destination: DynamoDBPrefixList # DynamoDB via Gateway Endpoint
```

**Network Flow**:

```
MCP Runtime Container
  ↓ (port 443)
  ├─→ VPC Endpoints (ECR, Logs, KMS, etc.)
  └─→ DynamoDB Gateway Endpoint
```

### AgentRuntimeSecurityGroup

Controls Agent Runtime container networking:

```yaml
Ingress: [] # No inbound - accessed via Bedrock HTTP endpoint

Egress:
  - Protocol: TCP
    Port: 443
    Destination: VPCEndpointSecurityGroup # Access to AWS services
```

**Network Flow**:

```
Agent Runtime Container
  ↓ (port 443)
  ├─→ Bedrock Runtime (invoke models)
  ├─→ Bedrock AgentCore (call MCP/Gateway)
  ├─→ RDS Data API (Aurora queries)
  ├─→ Secrets Manager (credentials)
  └─→ CloudWatch Logs (logging)
```

### GatewayLambdaSecurityGroup

Controls Lambda functions in Gateway stack:

```yaml
Ingress: [] # Lambdas don't receive direct connections

Egress:
  - Protocol: TCP
    Port: 443
    Destination: VPCEndpointSecurityGroup # AWS service access
  - Protocol: TCP
    Port: 443
    Destination: DynamoDBPrefixList # DynamoDB access
```

---

## 4. How Components Connect to VPC

### MCP Runtime (`mcp-server-stack.yaml`)

The MCP Runtime is deployed as a Bedrock AgentCore Runtime in VPC mode:

```yaml
MCPDynamoDBRuntime:
  Type: AWS::BedrockAgentCore::Runtime
  Properties:
    NetworkConfiguration:
      NetworkMode: "VPC"
      NetworkModeConfig:
        SecurityGroups:
          - MCPRuntimeSecurityGroup
        Subnets:
          - PrivateSubnet3 # Only in one subnet for this example
```

**Important**: AgentCore Runtime creates ENIs in the specified subnets. These ENIs:

- Take ~8 hours to automatically delete after stack deletion
- Are managed by the Bedrock service
- Have private IP addresses from the subnet CIDR

### Agent Runtime (`agent-server-stack.yaml`)

Similar VPC configuration:

```yaml
AgentRuntime:
  Type: AWS::BedrockAgentCore::Runtime
  Properties:
    NetworkConfiguration:
      NetworkMode: "VPC"
      NetworkModeConfig:
        SecurityGroups:
          - AgentRuntimeSecurityGroup
        Subnets:
          - PrivateSubnet1
```

### Container Images (ECR)

Both runtimes pull Docker images from ECR:

```yaml
AgentRuntimeArtifact:
  ContainerConfiguration:
    ContainerUri: !Sub "${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/${Repository}:build-1"
```

**Network Path for Image Pull**:

```
AgentCore Runtime (in VPC)
  ↓ (HTTPS)
  → ECR API Endpoint (ecr.api)
  → ECR Docker Endpoint (ecr.dkr)
  → S3 Gateway Endpoint (image layers stored in S3)
```

This requires:

1. `ecr.api` VPC endpoint for authentication
2. `ecr.dkr` VPC endpoint for image manifest
3. S3 Gateway endpoint for layer downloads
4. Proper IAM permissions for ECR access

---

## 5. Network Communication Flows

### End-to-End Request Flow

```
┌──────────────┐
│   External   │
│    Client    │
└──────┬───────┘
       │ (HTTPS)
       ↓
┌──────────────────────────────────────────────┐
│  Bedrock AgentCore Agent Runtime Endpoint    │
│  (Public HTTPS endpoint)                     │
└──────────────────┬───────────────────────────┘
                   │
                   ↓ (Internal Bedrock network)
       ┌───────────────────────┐
       │  Agent Runtime (VPC)  │
       │  PrivateSubnet1       │
       └───────────┬───────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
    ↓              ↓              ↓
┌─────────┐  ┌──────────┐  ┌──────────────┐
│ Bedrock │  │ Bedrock  │  │ RDS Data API │
│ Runtime │  │AgentCore │  │   Endpoint   │
│ Endpoint│  │ Endpoint │  └──────────────┘
└─────────┘  └────┬─────┘
                  │
    ┌─────────────┴─────────────┐
    │                           │
    ↓                           ↓
┌──────────────┐        ┌──────────────┐
│ MCP Runtime  │        │   Gateway    │
│ PrivateSubnet3│       │  (Lambda)    │
└──────┬───────┘        └──────┬───────┘
       │                       │
       ↓                       ↓
  ┌─────────────┐        ┌──────────────┐
  │  DynamoDB   │        │  DynamoDB    │
  │  (Gateway)  │        │  (Gateway)   │
  └─────────────┘        └──────────────┘
```

### Key Network Paths

1. **Agent calls Bedrock for LLM inference**:

   ```
   Agent Runtime → bedrock-runtime VPC endpoint → Claude model
   ```

2. **Agent calls MCP Runtime**:

   ```
   Agent Runtime → bedrock-agentcore VPC endpoint → MCP Runtime (via internal routing)
   ```

3. **Agent calls Gateway**:

   ```
   Agent Runtime → bedrock-agentcore.gateway VPC endpoint → Gateway → Lambda
   ```

4. **MCP accesses DynamoDB**:

   ```
   MCP Runtime → DynamoDB Gateway Endpoint → DynamoDB service
   ```

5. **Agent queries Aurora**:
   ```
   Agent Runtime → rds-data VPC endpoint → Aurora Serverless (Data API)
   ```

---

## 6. DynamoDB Gateway Endpoint Deep Dive

### Why Gateway Endpoint Instead of Interface?

**Gateway Endpoints** are preferred for DynamoDB and S3 because:

- **Free**: No hourly charges
- **Scalable**: Automatically scale with traffic
- **Simple**: Just route table entries

**Implementation**:

```yaml
DynamoDBGatewayEndpoint:
  Type: AWS::EC2::VPCEndpoint
  Properties:
    VpcEndpointType: Gateway
    ServiceName: !Sub "com.amazonaws.${AWS::Region}.dynamodb"
    RouteTableIds:
      - !Ref PrivateRouteTable # Adds route to all subnets
    PolicyDocument:
      Statement:
        - Effect: Allow
          Principal: "*"
          Action:
            - dynamodb:GetItem
            - dynamodb:Query
            - dynamodb:Scan
            - dynamodb:DescribeTable
          Resource:
            - !Sub "arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/*"
```

### Prefix List Configuration

For security group rules to allow DynamoDB traffic:

```yaml
Mappings:
  DynamoDBPrefixListIds:
    us-east-1: { PrefixListId: pl-02cd2c6b }
    us-east-2: { PrefixListId: pl-4ca54025 }
    us-west-1: { PrefixListId: pl-6ea54007 }
    us-west-2: { PrefixListId: pl-00a54069 }

# Used in security group:
MCPRuntimeToDynamoDBRule:
  Type: AWS::EC2::SecurityGroupEgress
  Properties:
    GroupId: !Ref MCPRuntimeSecurityGroup
    IpProtocol: tcp
    FromPort: 443
    ToPort: 443
    DestinationPrefixListId:
      !FindInMap [DynamoDBPrefixListIds, !Ref "AWS::Region", PrefixListId]
```

**Important**: To deploy in regions other than us-east-1, us-east-2, us-west-1, us-west-2, you must:

1. Find the DynamoDB prefix list ID for your region
2. Add it to the mapping in `vpc-stack.yaml`

---

## 7. Authentication & Authorization

### OAuth2 Flow for MCP and Gateway

Both MCP and Gateway use Cognito for authentication:

```
Agent Runtime
  ↓
  1. Gets OAuth2 token from Cognito (via bedrock-agentcore)
  ↓
  2. Calls MCP/Gateway with token
  ↓
  3. MCP/Gateway validates JWT against Cognito discovery URL
```

**Cognito Integration** (`cognito-stack.yaml`):

- **User Pool**: Machine-to-machine (M2M) authentication
- **Resource Server**: Defines custom scopes (read, write, gateway, agent)
- **App Clients**: Separate clients for Gateway, Agent, MCP
- **Client Credentials Flow**: Used for service-to-service auth

**Network Path**:

```
Runtime → secretsmanager VPC endpoint → Client credentials
        → Cognito (via HTTPS to internet) → OAuth2 token
```

**Note**: Cognito doesn't have a VPC endpoint, so OAuth2 token requests go via the internet. However, the runtime can cache tokens.

---

## 8. Observability & Monitoring

### VPC Flow Logs

```yaml
VPCFlowLog:
  Properties:
    ResourceType: VPC
    TrafficType: ALL # Accept, Reject, and All
    LogDestinationType: cloud-watch-logs
    DeliverLogsPermissionArn: !GetAtt VPCFlowLogRole.Arn
```

**Captured Information**:

- Source/Destination IPs
- Source/Destination Ports
- Protocol
- Accept/Reject decisions
- Useful for troubleshooting security group rules

### CloudWatch Logs

All logs sent through `logs` VPC endpoint:

- Agent Runtime application logs
- MCP Runtime application logs
- Lambda function logs
- VPC Flow Logs

### X-Ray Tracing

Distributed tracing through `xray` VPC endpoint:

- End-to-end request tracing
- Performance bottleneck identification
- Service map visualization

---

## 9. Cost Optimization Insights

### VPC Endpoint Costs (us-west-2)

**Interface Endpoints** (12 endpoints × 3 AZs × $0.01/hour):

- Cost per endpoint per AZ: $7.20/month
- Total for 3 AZs: $21.60/endpoint/month
- **Total**: ~$259/month for 12 interface endpoints

**Gateway Endpoints** (2 endpoints):

- **Free** - only pay for data transfer

**Data Processing**:

- $0.01 per GB processed through interface endpoints
- Gateway endpoints: no data processing charge

### Optimization Strategies

1. **Consolidate Subnets**: Deploy all resources in fewer subnets

   - Current: 3 subnets × 12 endpoints = 36 ENIs
   - Optimized: 2 subnets × 12 endpoints = 24 ENIs
   - Savings: ~$86/month

2. **Use Gateway Endpoints**: Already optimized for S3 and DynamoDB

3. **Single VPC**: Share VPC across multiple workloads

---

## 10. Deployment Architecture

### Stack Dependency Flow

```
┌─────────────┐
│  VPC Stack  │ ← Foundation (VPC, Subnets, Endpoints)
└──────┬──────┘
       │
   ┌───┴────────────────────┐
   │                        │
   ↓                        ↓
┌─────────┐         ┌──────────────┐
│ Cognito │         │   Aurora     │
│  Stack  │         │ DynamoDB     │
└────┬────┘         │   Stacks     │
     │              └──────┬───────┘
     │                     │
     └─────────┬───────────┘
               │
      ┌────────┴─────────┐
      │                  │
      ↓                  ↓
┌───────────┐     ┌─────────────┐
│  Gateway  │     │ MCP Server  │
│   Stack   │     │    Stack    │
└─────┬─────┘     └──────┬──────┘
      │                  │
      └────────┬─────────┘
               │
               ↓
        ┌────────────┐
        │   Agent    │
        │   Stack    │
        └────────────┘
```

### Network-Related Resources Per Stack

| Stack    | Network Resources                                          |
| -------- | ---------------------------------------------------------- |
| VPC      | VPC, Subnets, Route Tables, VPC Endpoints, Security Groups |
| Cognito  | None (SaaS service)                                        |
| Aurora   | DB Subnet Group, Aurora Security Group                     |
| DynamoDB | None (uses Gateway Endpoint)                               |
| Gateway  | Lambda in VPC, uses GatewayLambdaSecurityGroup             |
| MCP      | Runtime in VPC, uses MCPRuntimeSecurityGroup               |
| Agent    | Runtime in VPC, uses AgentRuntimeSecurityGroup             |

---

## 11. Important Networking Considerations

### ENI Cleanup

**Critical**: Bedrock AgentCore Runtimes create ENIs that take **~8 hours** to automatically delete:

```bash
# Deployment
./deploy.sh --email admin@example.com --password 'MyP@ss!'

# Cleanup (except VPC)
./cleanup.sh --delete-s3 --region us-west-2

# Wait ~8 hours for ENI deletion

# Delete VPC
./cleanup.sh --delete-vpc --region us-west-2
```

**Why?**: AWS retains ENIs for a cooling-off period to prevent premature deletion.

### Private DNS Resolution

All interface endpoints require DNS resolution to work:

```yaml
VPC:
  Properties:
    EnableDnsSupport: true # Required
    EnableDnsHostnames: true # Required

InterfaceEndpoint:
  Properties:
    PrivateDnsEnabled: true # Creates private Route53 records
```

**DNS Records Created**:

```
bedrock-runtime.us-west-2.amazonaws.com → 10.0.x.x (VPC endpoint IP)
```

Without these settings, services would try to reach AWS public endpoints, which would fail in a private VPC.

### Regional Considerations

**Supported in README**: us-west-2 only

**To support other regions**:

1. Update DynamoDB prefix list mapping
2. Verify all VPC endpoint services are available
3. Test Bedrock model availability

```bash
# Check available VPC endpoints
aws ec2 describe-vpc-endpoint-services --region us-east-1
```

---

## 12. Network Security Best Practices

### Implemented in This Architecture

✅ **No Internet Gateway**: Complete isolation from public internet  
✅ **No NAT Gateway**: No outbound internet access  
✅ **Least Privilege Security Groups**: Only required traffic allowed  
✅ **VPC Endpoints**: Private AWS service access  
✅ **Encryption in Transit**: TLS 1.2+ for all connections  
✅ **VPC Flow Logs**: Network monitoring and forensics  
✅ **Private Subnets Only**: No public IP assignments  
✅ **IAM Roles**: Service-specific permissions  
✅ **Secrets Manager**: No hardcoded credentials

### Additional Recommendations

1. **Network ACLs**: Add subnet-level firewall rules
2. **AWS PrivateLink**: For custom services
3. **Transit Gateway**: For multi-VPC architectures
4. **VPC Peering**: Connect to other VPCs if needed
5. **Session Manager**: For debugging (requires SSM endpoint)

---

## 13. Troubleshooting Network Issues

### Common Issues and Solutions

**Issue**: Container fails to pull from ECR

**Solution**:

```bash
# Check VPC endpoints exist
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=vpc-xxx"

# Verify security group rules
aws ec2 describe-security-groups --group-ids sg-xxx

# Check route tables
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=vpc-xxx"
```

**Issue**: MCP cannot access DynamoDB

**Solution**:

```bash
# Verify Gateway Endpoint exists
aws ec2 describe-vpc-endpoints --filters "Name=service-name,Values=com.amazonaws.us-west-2.dynamodb"

# Check security group allows prefix list
aws ec2 describe-security-groups --group-ids sg-xxx --query 'SecurityGroups[].IpPermissionsEgress'

# Test from runtime logs
grep "dynamodb" /aws/bedrock-agentcore/runtimes/*
```

**Issue**: Agent cannot reach Bedrock

**Solution**:

```bash
# Check bedrock-runtime endpoint
aws ec2 describe-vpc-endpoints --filters "Name=service-name,Values=com.amazonaws.us-west-2.bedrock-runtime"

# Verify DNS resolution working
# (requires Session Manager access to VPC)
nslookup bedrock-runtime.us-west-2.amazonaws.com
```

### Using VPC Flow Logs for Debugging

```bash
# Find rejected connections
aws logs filter-log-events \
  --log-group-name /aws/vpc/flow-logs \
  --filter-pattern "[version, account_id, eni_id, source, destination, srcport, destport, protocol, packets, bytes, start, end, action=REJECT, log_status]" \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --limit 20
```

---

## 14. Key Takeaways

### Architecture Highlights

1. **Zero Internet Dependency**: Entire stack runs in private subnets
2. **VPC Endpoints Enable Everything**: All AWS services accessed privately
3. **Security Groups Control All Traffic**: Fine-grained network access control
4. **Multi-AZ Design**: High availability across 3 availability zones
5. **Separation of Concerns**: Different security groups for different runtimes
6. **Gateway Endpoints for Cost**: DynamoDB and S3 use free gateway endpoints
7. **OAuth2 for Auth**: Cognito-based machine-to-machine authentication
8. **Full Observability**: VPC Flow Logs, CloudWatch, X-Ray tracing

### When to Use This Pattern

✅ **Highly regulated industries**: Healthcare, finance, government  
✅ **Compliance requirements**: HIPAA, PCI-DSS, FedRAMP  
✅ **Sensitive data processing**: PII, PHI, financial data  
✅ **Zero-trust architecture**: No internet access requirement  
✅ **Hybrid cloud**: Connect to on-premises via Direct Connect/VPN

### When NOT to Use This Pattern

❌ **Public-facing APIs**: Requires public endpoints  
❌ **Internet-dependent tools**: npm, pip, external APIs  
❌ **Development/Testing**: Too complex for quick iteration  
❌ **Cost-sensitive**: VPC endpoints add ~$260/month

---

## 15. Comparison: VPC vs Non-VPC Deployment

| Aspect                | VPC Deployment              | Non-VPC (Default)                |
| --------------------- | --------------------------- | -------------------------------- |
| **Network Isolation** | Complete                    | Shared AWS infrastructure        |
| **Internet Access**   | None                        | Full (via AWS network)           |
| **Security**          | VPC security groups         | Service-managed                  |
| **Compliance**        | Easier to meet requirements | May not meet strict requirements |
| **Cost**              | +$260/month for endpoints   | No VPC endpoint costs            |
| **Complexity**        | High                        | Low                              |
| **Setup Time**        | 30-45 minutes               | 5-10 minutes                     |
| **Integration**       | Requires VPC endpoints      | Direct AWS service access        |
| **Use Case**          | Regulated, enterprise       | General purpose                  |

---

## Conclusion

The customer-support-assistant-vpc example showcases a **production-grade, enterprise-ready networking architecture** for Bedrock AgentCore. By leveraging VPC endpoints, private subnets, and security groups, it creates a completely isolated environment that meets stringent security and compliance requirements while maintaining full functionality.

The key networking innovation is the use of **13 VPC endpoints** to provide private access to all required AWS services, eliminating any need for internet connectivity. This architecture pattern can be adapted for various use cases requiring maximum security and isolation.

---

## References

- [VPC Endpoints Documentation](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints.html)
- [Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)
- [DynamoDB Gateway Endpoints](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/vpc-endpoints-dynamodb.html)

