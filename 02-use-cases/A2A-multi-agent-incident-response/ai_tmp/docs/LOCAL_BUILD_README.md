# Building and Deploying from Local Source

This guide shows how to use **YOUR local source code** instead of pulling from GitHub.

## Quick Start

Build and deploy all agents from local source:

```bash
./build_and_deploy_local.sh
```

This will:
1. ✅ Build Docker images from YOUR local code
2. ✅ Push images to your ECR repositories  
3. ✅ Lambda auto-updates runtimes with new images
4. ✅ All agents restart with your local changes

## When to Use This

Use local builds when you:
- ✅ Modified agent source code (`agent.py`, `main.py`, etc.)
- ✅ Changed Dockerfiles
- ✅ Don't want to commit/push to GitHub yet
- ✅ Want to test local changes immediately
- ✅ Changed default model IDs in code
- ✅ Don't trust public GitHub repository

## What Gets Built

**All 3 agents from your local directories:**

1. **Web Search Agent** (`web_search_openai_agents/`)
   - Your `agent.py` with `gpt-4o-mini` default
   - Your Dockerfile
   - Your requirements

2. **Host Agent** (`host_adk_agent/`)
   - Your `main.py` and `agent.py`
   - Your Dockerfile
   - Your dependencies

3. **Monitoring Agent** (`monitoring_strands_agent/`)
   - Your `main.py` with `boto3` import fix
   - Your Dockerfile
   - Your configuration

## Comparison with Other Methods

| Method | Source | Speed | Use When |
|--------|--------|-------|----------|
| `./build_and_deploy_local.sh` | **Your local files** | Medium (2-3 min) | Testing local changes |
| `./update_api_keys.sh --force` | GitHub repo | Slow (3-5 min) | Key updates + GitHub code |
| `./update_api_keys.sh` | N/A (env vars only) | Fast (1-2 min) | Just API key changes |

## How It Works

### Step 1: Build Locally
```bash
cd web_search_openai_agents/
docker build -t web-search-agent:local .
```

### Step 2: Tag for ECR
```bash
docker tag web-search-agent:local \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO:local-123456789
```

### Step 3: Push to ECR
```bash
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO:local-123456789
```

### Step 4: Lambda Auto-Update
- ECR push triggers EventBridge rule
- Lambda function gets notification
- Lambda updates BedrockAgentCore Runtime with new image
- Runtime restarts with your local code

## Verify Your Changes

After running the script:

```bash
# Check if agents restarted (should be < 2 min ago)
aws logs tail "/aws/bedrock-agentcore/runtimes/websearchagenta2a-n8Gd2BHGsy-DEFAULT" \
  --region us-east-1 --since 2m --format short | grep "startup complete"
```

## Troubleshooting

**Docker not found:**
```bash
# Install Docker Desktop or:
brew install docker
```

**ECR login fails:**
```bash
# Re-authenticate AWS
ke_aws ai-dev
```

**Build fails:**
```bash
# Check Dockerfile in the agent directory
# Common issue: missing dependencies in requirements.txt
```

**Lambda didn't update runtime:**
```bash
# Check Lambda logs
aws logs tail "/aws/lambda/web-search-agent-a2a-ECRImageNotificationFunction-..." \
  --region us-east-1 --since 5m
```

## Making It Permanent

To stop using GitHub builds entirely:

1. **Option A**: Keep using this script whenever you make changes
   ```bash
   # Edit code
   vim web_search_openai_agents/agent.py
   
   # Deploy
   ./build_and_deploy_local.sh
   ```

2. **Option B**: Disable CodeBuild in CloudFormation
   - Remove the CodeBuild project from templates
   - Redeploy stacks
   - Always use local builds

## Best Practices

✅ **Test locally first:**
```bash
cd web_search_openai_agents/
docker build -t test .
docker run -e OPENAI_API_KEY=test -e MODEL_ID=gpt-4o-mini test
```

✅ **Tag your builds:** Script automatically tags with timestamp

✅ **Keep local changes:** Don't have to commit to GitHub

✅ **Version control:** Can always revert to GitHub builds

## Related Scripts

- `update_api_keys.sh` - Update API keys only (no rebuild)
- `update_api_keys.sh --force` - Rebuild from GitHub + update keys
- `build_and_deploy_local.sh` - Rebuild from local + deploy (this script)


