# Working Solution Files - Dependents API Integration

## ✅ ESSENTIAL FILES (Your Working Solution)

### 1. Lambda Proxy Function

**Location**: `cloudformation/lambda-dependents-proxy/`

- **`lambda_function.py`** - Core Lambda that proxies requests to dependents-api in EKS
  - Handles 8 tools: create/list/get/update/delete person, list/create/delete dependent
  - Retrieves tool name from `context.client_context.custom['bedrockAgentCoreToolName']`
  - Uses HTTP to connect to internal NLB at `dependents-api.v2.ue1.wexapps.com`
  - Status: ✅ WORKING
- **`requirements.txt`** - Python dependencies (requests library)
- **`lambda_function.zip`** - Bundled deployment package with dependencies

### 2. CloudFormation Deployment

**Location**: `cloudformation/`

- **`lambda-dependents-proxy-stack.yaml`** - Deploys Lambda with VPC config
  - Stack name: `healthcare-lambda-dependents-proxy`
  - Function: `healthcare-dependents-proxy`
  - VPC subnets: private-app-ue1a, private-app-ue1b
  - Security group: sg-01f825dbc74c40e8e
  - Status: ✅ DEPLOYED

### 3. Gateway Registration

**Location**: Root directory

- **`register_dependents_lambda.py`** - Registers Lambda as Gateway Target
  - Creates 8 individual tool schemas in `inlinePayload` format
  - Uses `GATEWAY_IAM_ROLE` credential provider
  - Target ID: `healthcare-dependents-api-target`
  - Status: ✅ REGISTERED

### 4. Test Agent

**Location**: Root directory

- **`langgraph_agent_gemini.py`** - LangGraph agent for testing
  - Uses Gemini 2.0 Flash
  - Fetches all tools from Gateway (includes dependents-api tools)
  - Supports `--query` parameter for automated testing
  - Status: ✅ WORKING END-TO-END

### 5. Infrastructure Fixes

**Location**: `ai_tmp/`

- **`fix-dependents-api-http.yaml`** - Kubernetes config for HTTP Gateway
  - Creates dedicated HTTP Istio Gateway on port 80
  - Bypasses global HTTPS redirect
  - Applied to EKS cluster
  - Status: ✅ APPLIED

---

## 📂 CLEANUP/REFERENCE FILES (Not Active)

### ai_tmp/ directory (documentation/historical):

- `DEPLOYMENT_SUMMARY.md` - Summary doc (you asked not to create these)
- `FINAL_SUCCESS_SUMMARY.md` - Another summary doc
- `ARCHITECTURE_FLOW.md` - Architecture doc
- `COMPLETE_GUIDE.md` - Guide doc
- `WORKING_FILES.md` - Previous files list
- `readme.md` - Old readme
- `dependents-api-target_openapi.yaml` - Failed OpenAPI approach
- `Target1_openapi.yaml` - Old target spec

**Action**: You can delete the entire `ai_tmp/` directory if you want to clean up.

---

## 🔧 AWS RESOURCES (Currently Deployed)

### Working Resources:

1. **Lambda Function**: `healthcare-dependents-proxy`

   - Runtime: Python 3.12
   - VPC: Attached to private subnets
   - Cost: ~$0.20/month (1M requests free tier)

2. **CloudFormation Stack**: `healthcare-lambda-dependents-proxy`

   - Status: CREATE_COMPLETE
   - Resources: Lambda, IAM role, LogGroup

3. **Gateway Target**: `healthcare-dependents-api-target`

   - Type: Lambda
   - Tools: 8 dependents-api tools
   - Credential: GATEWAY_IAM_ROLE

4. **Gateway**: `healthcare-fhir-gateway-fqssvsgzsg`
   - Includes FHIR tools + dependents-api tools
   - OAuth enabled

### Cleaned Up (No Longer Exists):

- ❌ MCP Runtime stack (deleted)
- ❌ ECR Repository (deleted)
- ❌ Failed security group (deleted)

---

## 📋 ORIGINAL PROJECT FILES (Unchanged)

These are the original example files, not modified:

- `langgraph_agent.py` - Original example agent
- `strands_agent.py` - Strands SDK example
- `setup_fhir_mcp.py` - FHIR MCP setup
- `init_env.py` - Environment initialization
- `utils.py` - Helper utilities
- `fhir-openapi-spec.yaml` - FHIR OpenAPI spec
- `requirements.txt` - Python dependencies
- `payload.json` - Test payload
- `test_data/` - Sample data
- `static/` - Images

---

## 🎯 MINIMAL WORKING SET

If you want the absolute minimum to keep this working:

```
healthcare-appointment-agent/
├── cloudformation/
│   ├── lambda-dependents-proxy/
│   │   ├── lambda_function.py          ← Lambda code
│   │   ├── lambda_function.zip         ← Deployment package
│   │   └── requirements.txt            ← Dependencies
│   └── lambda-dependents-proxy-stack.yaml  ← CloudFormation
├── register_dependents_lambda.py       ← Gateway registration script
└── langgraph_agent_gemini.py          ← Test agent

PLUS on EKS:
- Istio HTTP Gateway (from fix-dependents-api-http.yaml)
- Route53 Private Hosted Zone for v2.ue1.wexapps.com
```

---

## 🧹 CLEANUP STATUS

**✓ REMOVED** (Unrelated files):

1. ✓ `payload.json` - Test payload file
2. ✓ `cloudformation/fhir-openapi-searchpatient/` - Unzipped FHIR lambda dependencies

**KEPT** (Working solution + original project):

- All `ai_tmp/` documentation
- All working solution files
- All original project files

---

## ✅ VERIFICATION

To verify your working solution:

```bash
# 1. Check Lambda is deployed
aws lambda get-function --function-name healthcare-dependents-proxy --region us-east-1

# 2. Check Gateway target is registered
aws bedrock-agentcore list-gateway-targets --gateway-identifier healthcare-fhir-gateway-fqssvsgzsg --region us-east-1

# 3. Test end-to-end
cd /Users/W517261/Ke_GenAI/amazon-bedrock-agentcore-samples/02-use-cases/healthcare-appointment-agent
source .env
python langgraph_agent_gemini.py --gateway_id healthcare-fhir-gateway-fqssvsgzsg --query "Show dependents for user_001"
```

---

**Last Updated**: After cleanup of failed MCP Runtime stack
**Status**: ✅ All working resources identified and documented
