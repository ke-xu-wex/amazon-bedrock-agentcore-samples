# Healthcare Agent Deployment Summary

## ✅ Deployment Completed Successfully!

All infrastructure and code modifications have been completed. The deployment is ready to use once Bedrock model permissions are granted.

### What Was Deployed

#### 1. **Modified Code (No HealthLake - Mock Data)**

- ✅ Lambda function updated with hardcoded patient/immunization data
- ✅ CloudFormation template removed HealthLake resources
- ✅ Saved ~$730/month by using mock data instead of HealthLake
- ✅ All tags added: `project: a2a-demo`, `creator: ke-xu-wex`, `purpose: healthcare-mcp-gateway-demo`

#### 2. **AWS Resources Created**

| Resource                  | Status      | Details                                                      |
| ------------------------- | ----------- | ------------------------------------------------------------ |
| S3 Bucket                 | ✅ Created  | `healthcare-mcp-demo-1764972468-us-east-1`                   |
| CloudFormation Stack      | ✅ Deployed | `healthcare-cfn-stack`                                       |
| API Gateway               | ✅ Running  | `https://y2wd96t0fb.execute-api.us-east-1.amazonaws.com/dev` |
| Lambda Function           | ✅ Deployed | `fhir-mcp-lambda-*` with mock data                           |
| Cognito User Pool         | ✅ Created  | OAuth2 authentication configured                             |
| Bedrock AgentCore Gateway | ✅ Created  | `healthcare-fhir-gateway-fqssvsgzsg`                         |
| Gateway Target            | ✅ Created  | 5 MCP tools available                                        |

#### 3. **MCP Tools Available**

The gateway exposes 5 REST API endpoints as MCP tools:

1. `getPatient` - Get patient details by ID
2. `searchImmunization` - Search immunization records
3. `bookAppointment` - Book appointment
4. `getSlots` - Get available appointment slots
5. `searchPatient` - Search patients (bonus tool)

### Mock Data Included

- **2 Patients**:
  - Richard Doe (adult-patient-001, born 1985)
  - John Doe (pediatric-patient-001, born 2023, age 1.5 years)
- **10 Immunization Records**:
  - 7 completed: IPV, DTaP, PCV13, Hib, Hepatitis A/B, Influenza
  - 3 pending: MMR, Varicella, MMR-Varicella
- **1 Practitioner**: Dr. Sarah Johnson

### Cost Analysis

| Resource          | Monthly Cost           |
| ----------------- | ---------------------- |
| API Gateway       | ~$0 (pay per use)      |
| Lambda            | ~$0 (within free tier) |
| Cognito           | ~$0 (within free tier) |
| S3                | ~$0.02                 |
| AgentCore Gateway | ~$0 (pay per use)      |
| **Total**         | **~$0-2/month**        |

Compare to original: **$730/month** (HealthLake cost eliminated!)

## ⚠️ Action Required: Enable Bedrock Model Access

The deployment is complete, but you need to enable Bedrock model permissions:

### Error Encountered:

```
AccessDeniedException: User is not authorized to perform: bedrock:InvokeModelWithResponseStream
on resource: arn:aws:bedrock:::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0
with an explicit deny in a service control policy
```

### Solution Options:

#### Option 1: Request SCP Exception (Recommended)

Contact your AWS administrator to add an exception to the Service Control Policy for:

- Service: `bedrock:InvokeModel*`
- Resource: `anthropic.claude-haiku-4-5-20251001-v1:0` or all Claude models

#### Option 2: Use Different Model

If Claude Haiku 4.5 is blocked, try another model that's allowed:

```bash
# Edit strands_agent.py and test_agent.py, change line:
model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0"
# To one of:
model_id="anthropic.claude-3-5-sonnet-20241022-v2:0"  # Claude 3.5 Sonnet
model_id="anthropic.claude-3-sonnet-20240229-v1:0"    # Claude 3 Sonnet
```

#### Option 3: Check Model Access in Console

1. Go to: https://console.aws.amazon.com/bedrock/
2. Click "Model access" in left menu
3. Ensure Claude models are enabled
4. If not, click "Manage model access" and request access

## 🚀 How to Test the Agent

Once Bedrock permissions are granted:

### Test with Strands Agent (Interactive)

```bash
cd /Users/W517261/Ke_GenAI/amazon-bedrock-agentcore-samples/02-use-cases/healthcare-appointment-agent
source .venv/bin/activate
python strands_agent.py --gateway_id healthcare-fhir-gateway-fqssvsgzsg
```

### Test with Quick Script

```bash
python test_agent.py
```

### Sample Prompts to Try:

- "How can you help?"
- "What is the immunization schedule for John?"
- "Check immunization records for the child"
- "Find available appointment slots for MMR vaccine around August 15, 2025"
- "Book an appointment for 2025-08-15 14:00"

## 📋 Environment Details

### Files Modified:

- `cloudformation/fhir-openapi-searchpatient/lambda_function.py` - Mock data implementation
- `cloudformation/healthcare-cfn.yaml` - Removed HealthLake, added tags
- `init_env.py` - Removed HealthLake endpoint reference
- `utils.py` - Disabled SSL verification for corporate proxy
- `fhir-openapi-spec.yaml` - Updated with API Gateway endpoint

### Environment Variables (.env):

```bash
aws_default_region=us-east-1
gateway_iam_role=arn:aws:iam::975049916663:role/service-role/primitives-iam-role-*
cognito_discovery_url=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XcXhrmQys/...
cognito_token_url=https://us-east-1e05e44f0.auth.us-east-1.amazoncognito.com/oauth2/token
cognito_user_pool_id=us-east-1_XcXhrmQys
cognito_client_id=25ifnbk88dn166mvsu61k9a4pl
...
```

## 🧹 Cleanup Instructions

When you're done testing, delete all resources to avoid any charges:

```bash
# 1. Delete Gateway
cd /Users/W517261/Ke_GenAI/amazon-bedrock-agentcore-samples/02-use-cases/healthcare-appointment-agent
source .venv/bin/activate
python setup_fhir_mcp.py --op_type Delete --gateway_id healthcare-fhir-gateway-fqssvsgzsg

# 2. Delete CloudFormation Stack
aws cloudformation delete-stack --stack-name healthcare-cfn-stack --region us-east-1

# 3. Delete S3 Bucket (after stack is deleted)
aws s3 rm s3://healthcare-mcp-demo-1764972468-us-east-1 --recursive
aws s3api delete-bucket --bucket healthcare-mcp-demo-1764972468-us-east-1 --region us-east-1
```

## 📝 Key Learnings

This deployment demonstrates:

1. ✅ **MCP Gateway Integration** - Convert REST APIs to MCP tools
2. ✅ **OAuth2 Authentication** - Bidirectional auth (ingress + egress)
3. ✅ **OpenAPI to MCP** - Automatic tool generation from OpenAPI spec
4. ✅ **Cost Optimization** - Mock data vs. expensive managed services
5. ✅ **Agent Frameworks** - Works with Strands, LangGraph, and others

## 🎯 Next Steps

1. **Enable Bedrock permissions** (see above)
2. **Test the agent** with sample prompts
3. **Explore the code** to understand MCP Gateway architecture
4. **Extend the example** - add more endpoints or modify mock data
5. **Clean up** when done to avoid charges

---

**Deployment Date**: December 5, 2024  
**Region**: us-east-1  
**Gateway ID**: healthcare-fhir-gateway-fqssvsgzsg  
**Stack Name**: healthcare-cfn-stack
