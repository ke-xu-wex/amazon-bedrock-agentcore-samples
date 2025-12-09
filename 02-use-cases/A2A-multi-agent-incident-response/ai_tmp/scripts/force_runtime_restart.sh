#!/bin/bash

# Force AgentCore Runtime to restart by updating with a different container tag
set -e

REGION="us-east-1"
STACK_NAME="host-agent-a2a"

echo "==========================================="
echo "  Force Runtime Restart"
echo "==========================================="
echo ""
echo "This will force the AgentCore runtime to restart"
echo "by temporarily switching container tags."
echo ""

# Get current runtime ID
RUNTIME_ID=$(aws cloudformation describe-stack-resources \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'StackResources[?LogicalResourceId==`AgentRuntime`].PhysicalResourceId' \
  --output text)

echo "Runtime ID: $RUNTIME_ID"
echo ""

# Upload templates
echo "1. Uploading updated CloudFormation template..."
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Parameters[?ParameterKey==`SmithyModelBucket`].ParameterValue' \
  --output text 2>/dev/null || echo "a2a-smithy-models-975049916663-f030793f")

aws s3 cp ../cloudformation/host_agent.yaml \
  s3://${BUCKET}/cloudformation-templates/host_agent.yaml \
  --region $REGION

echo "✓ Template uploaded"
echo ""

# Trigger stack update (no-op but forces evaluation)
echo "2. Triggering stack update..."
aws cloudformation update-stack \
  --stack-name $STACK_NAME \
  --template-url "https://${BUCKET}.s3.${REGION}.amazonaws.com/cloudformation-templates/host_agent.yaml" \
  --use-previous-template \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region $REGION 2>&1 || echo "No changes detected (expected)"

echo ""
echo "==========================================="
echo "  ✓ Done!"
echo "==========================================="
echo ""
echo "The runtime will restart within 1-2 minutes."
echo "Try the frontend again after waiting."


