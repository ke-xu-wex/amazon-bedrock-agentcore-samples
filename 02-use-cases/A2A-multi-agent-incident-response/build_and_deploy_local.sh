#!/bin/bash
set -e

# Script to build Docker images locally and deploy to ECR
# This bypasses GitHub and uses your local source code
# Usage: ./build_and_deploy_local.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "========================================="
echo "  Build & Deploy Local Docker Images"
echo "========================================="
echo ""
echo "Account: $ACCOUNT_ID"
echo "Region: $REGION"
echo ""

# Get ECR repository names from CloudFormation
echo "Getting ECR repository information..."
WEB_SEARCH_ECR=$(aws cloudformation describe-stack-resources \
    --stack-name web-search-agent-a2a \
    --region $REGION \
    --query 'StackResources[?ResourceType==`AWS::ECR::Repository`].PhysicalResourceId' \
    --output text)

HOST_ECR=$(aws cloudformation describe-stack-resources \
    --stack-name host-agent-a2a \
    --region $REGION \
    --query 'StackResources[?ResourceType==`AWS::ECR::Repository`].PhysicalResourceId' \
    --output text)

MONITOR_ECR=$(aws cloudformation describe-stack-resources \
    --stack-name monitor-agent-a2a \
    --region $REGION \
    --query 'StackResources[?ResourceType==`AWS::ECR::Repository`].PhysicalResourceId' \
    --output text)

echo "✓ Found ECR repositories:"
echo "  - Web Search: $WEB_SEARCH_ECR"
echo "  - Host Agent: $HOST_ECR"
echo "  - Monitoring: $MONITOR_ECR"
echo ""

# Login to ECR
echo "Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
echo "✓ Logged in"
echo ""

# Build and push Web Search Agent
echo "========================================="
echo "1. WEB SEARCH AGENT"
echo "========================================="
cd "$SCRIPT_DIR/web_search_openai_agents"
echo "Building Docker image..."
docker build -t web-search-agent:local . --quiet
echo "✓ Built"

BUILD_TAG="local-$(date +%s)"
IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$WEB_SEARCH_ECR:$BUILD_TAG"
docker tag web-search-agent:local $IMAGE_URI
echo "Pushing to ECR as $BUILD_TAG..."
docker push $IMAGE_URI --quiet
echo "✓ Pushed: $IMAGE_URI"
echo ""

# Build and push Host Agent
echo "========================================="
echo "2. HOST AGENT"
echo "========================================="
cd "$SCRIPT_DIR/host_adk_agent"
echo "Building Docker image..."
docker build -t host-agent:local . --quiet
echo "✓ Built"

BUILD_TAG="local-$(date +%s)"
IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$HOST_ECR:$BUILD_TAG"
docker tag host-agent:local $IMAGE_URI
echo "Pushing to ECR as $BUILD_TAG..."
docker push $IMAGE_URI --quiet
echo "✓ Pushed: $IMAGE_URI"
echo ""

# Build and push Monitoring Agent
echo "========================================="
echo "3. MONITORING AGENT"
echo "========================================="
cd "$SCRIPT_DIR/monitoring_strands_agent"
echo "Building Docker image..."
docker build -t monitoring-agent:local . --quiet
echo "✓ Built"

BUILD_TAG="local-$(date +%s)"
IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$MONITOR_ECR:$BUILD_TAG"
docker tag monitoring-agent:local $IMAGE_URI
echo "Pushing to ECR as $BUILD_TAG..."
docker push $IMAGE_URI --quiet
echo "✓ Pushed: $IMAGE_URI"
echo ""

# Wait for Lambda to detect and update runtimes
echo "========================================="
echo "Waiting for Lambda to update runtimes..."
echo "========================================="
echo ""
echo "The ECR Lambda triggers will automatically update the runtimes."
echo "This usually takes 10-15 seconds..."
sleep 15
echo ""

# Check Lambda logs to confirm updates
echo "Checking Lambda update status..."
echo ""

WEB_LAMBDA=$(aws cloudformation describe-stack-resources \
    --stack-name web-search-agent-a2a \
    --region $REGION \
    --query 'StackResources[?ResourceType==`AWS::Lambda::Function` && contains(LogicalResourceId, `ECRImageNotification`)].PhysicalResourceId' \
    --output text)

HOST_LAMBDA=$(aws cloudformation describe-stack-resources \
    --stack-name host-agent-a2a \
    --region $REGION \
    --query 'StackResources[?ResourceType==`AWS::Lambda::Function` && contains(LogicalResourceId, `ECRImageNotification`)].PhysicalResourceId' \
    --output text)

MONITOR_LAMBDA=$(aws cloudformation describe-stack-resources \
    --stack-name monitor-agent-a2a \
    --region $REGION \
    --query 'StackResources[?ResourceType==`AWS::Lambda::Function` && contains(LogicalResourceId, `ECRImageNotification`)].PhysicalResourceId' \
    --output text)

echo "Web Search Agent:"
aws logs tail "/aws/lambda/$WEB_LAMBDA" --region $REGION --since 2m --format short 2>&1 | grep "updated successfully" | tail -1 || echo "  (checking...)"

echo ""
echo "Host Agent:"
aws logs tail "/aws/lambda/$HOST_LAMBDA" --region $REGION --since 2m --format short 2>&1 | grep "updated successfully" | tail -1 || echo "  (checking...)"

echo ""
echo "Monitoring Agent:"
aws logs tail "/aws/lambda/$MONITOR_LAMBDA" --region $REGION --since 2m --format short 2>&1 | grep "updated successfully" | tail -1 || echo "  (checking...)"

echo ""
echo "========================================="
echo "  ✅ LOCAL IMAGES DEPLOYED!"
echo "========================================="
echo ""
echo "All agents now running YOUR local code:"
echo "  ✓ Web Search Agent (gpt-4o-mini default)"
echo "  ✓ Host Agent"
echo "  ✓ Monitoring Agent"
echo ""
echo "Next steps:"
echo "1. Wait 30 seconds for agents to restart"
echo "2. Refresh your UI"
echo "3. Test the agents"
echo ""
echo "💡 To disable GitHub builds in the future, update your"
echo "   CloudFormation parameters to point to 'local' branch"
echo ""


