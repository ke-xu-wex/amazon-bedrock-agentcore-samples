# Healthcare Appointment Agent - Working Files

## ✅ Clean Directory Structure

After cleanup, here are the working files:

### Core Agent Files

| File | Purpose | Status |
|------|---------|--------|
| `langgraph_agent_gemini.py` | Main agent using Google Gemini 2.5 Flash | ✅ Working |
| `langgraph_agent.py` | Original agent using AWS Bedrock | ⚠️ Blocked by SCP |
| `strands_agent.py` | Strands agent implementation | ✅ Working |
| `utils.py` | Utility functions (Gateway, OAuth, etc.) | ✅ Working |

### Setup & Configuration

| File | Purpose | Status |
|------|---------|--------|
| `setup_fhir_mcp.py` | Setup FHIR API Gateway target | ✅ Working |
| `register_dependents_lambda.py` | Register Lambda proxy for dependents-api | ✅ Working |
| `init_env.py` | Initialize environment variables from CFN | ✅ Working |
| `fhir-openapi-spec.yaml` | OpenAPI spec for healthcare FHIR API | ✅ Working |
| `requirements.txt` | Python dependencies | ✅ Working |

### CloudFormation Templates

| File | Purpose | Cost |
|------|---------|------|
| `cloudformation/healthcare-cfn.yaml` | Main healthcare resources (API Gateway, Lambda, Cognito) | ~$2/month |
| `cloudformation/lambda-dependents-proxy-stack.yaml` | Lambda proxy for dependents-api | ~$0.20/month |

### Lambda Code

| Directory | Purpose | Status |
|-----------|---------|--------|
| `cloudformation/fhir-openapi-searchpatient/` | Healthcare FHIR Lambda (with mock data) | ✅ Deployed |
| `cloudformation/lambda-dependents-proxy/` | Dependents-API Lambda proxy | ✅ Deployed |

### Reference Documentation

| File | Purpose |
|------|---------|
| `readme.md` | Original example documentation |
| `COMPLETE_GUIDE.md` | Comprehensive implementation guide |
| `DEPLOYMENT_SUMMARY.md` | Deployment checklist |
| `ARCHITECTURE_FLOW.md` | Architecture diagrams |

### Working Artifacts (`ai_tmp/`)

| File | Purpose |
|------|---------|
| `FINAL_SUCCESS_SUMMARY.md` | **Final working solution documentation** |
| `dependents-api-target_openapi.yaml` | Dependents-API OpenAPI spec |
| `Target1_openapi.yaml` | Healthcare FHIR OpenAPI spec |
| `fix-dependents-api-http.yaml` | Istio Gateway config for HTTP |
| `DNS_FIX_COMMANDS.sh` | Route53 DNS setup commands |

## 🚀 Quick Start

### 1. Test the Agent

```bash
# Interactive mode
python langgraph_agent_gemini.py --gateway_id healthcare-fhir-gateway-fqssvsgzsg

# Single query mode (automated testing)
python langgraph_agent_gemini.py \
  --gateway_id healthcare-fhir-gateway-fqssvsgzsg \
  --query "Show dependents for user_001"
```

### 2. Register Additional Lambda Tools

If you need to update the dependents-api tools:

```bash
python register_dependents_lambda.py
```

### 3. Update FHIR Gateway Target

If you need to update the healthcare FHIR API:

```bash
python setup_fhir_mcp.py
```

## 📁 What Was Removed

Cleaned up 30+ temporary files including:
- ❌ Failed MCP Runtime attempt files
- ❌ Failed PrivateLink attempt scripts
- ❌ Intermediate troubleshooting .md files
- ❌ Test scripts and debug code
- ❌ Python cache directories
- ❌ Build artifacts

## 📊 Current Deployment

### AgentCore Gateway Targets
1. **Target1** (healthcare FHIR API)
   - 4 tools: getPatient, searchImmunization, bookAppointment, getSlots
   
2. **dependents-api-lambda-proxy** (Lambda proxy)
   - 8 tools: list_persons, get_person, create_person, update_person, delete_person, list_dependents, create_dependent, delete_dependent

### Total: 13 tools available to agents

## 🎯 Key Learnings

1. **Lambda + Gateway Pattern**: Tool name comes from `context.client_context.custom['bedrockAgentCoreToolName']`
2. **No Discriminator Needed**: Gateway handles routing, Lambda just looks at context
3. **Bundle Dependencies**: Lambda zip must include all Python libraries
4. **Private API Access**: Lambda in VPC → Internal NLB → EKS works perfectly

## 💰 Total Cost

- Healthcare FHIR API: ~$2/month (API Gateway + Lambda)
- Dependents Lambda Proxy: ~$0.20/month
- Route53 Private Zone: ~$0.50/month
- **Total: ~$2.70/month**

## 📚 Documentation

See `ai_tmp/FINAL_SUCCESS_SUMMARY.md` for complete implementation details, architecture, and troubleshooting guide.

