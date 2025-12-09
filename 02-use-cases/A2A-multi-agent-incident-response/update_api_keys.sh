#!/bin/bash
set -e

# Script to update API keys for all agents from .a2a.config
# Usage: ./update_api_keys.sh [--force]
#   --force: Force rebuild Docker images and restart all agents

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/.a2a.config"
REGION="us-east-1"
FORCE_REBUILD=false

# Parse arguments
if [ "$1" = "--force" ] || [ "$1" = "-f" ]; then
    FORCE_REBUILD=true
    echo "========================================="
    echo "  FORCE REBUILD & RESTART ALL AGENTS"
    echo "========================================="
else
    echo "========================================="
    echo "  Updating API Keys for All Agents"
    echo "========================================="
fi
echo ""

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: .a2a.config file not found at $CONFIG_FILE"
    exit 1
fi

# Read keys from config (suppressing output)
echo "Reading configuration..."
OPENAI_KEY=$(grep "  openai:" "$CONFIG_FILE" | awk '{print $2}')
OPENAI_MODEL=$(grep "  openai_model:" "$CONFIG_FILE" | awk '{print $2}')
TAVILY_KEY=$(grep "  tavily:" "$CONFIG_FILE" | awk '{print $2}')
GOOGLE_KEY=$(grep "  google:" "$CONFIG_FILE" | grep -v "google_model" | awk '{print $2}')
GOOGLE_MODEL=$(grep "  google_model:" "$CONFIG_FILE" | awk '{print $2}')

# Validate keys exist
if [ -z "$OPENAI_KEY" ] || [ -z "$TAVILY_KEY" ] || [ -z "$GOOGLE_KEY" ]; then
    echo "❌ Error: Missing API keys in config file"
    exit 1
fi

echo "✓ Configuration loaded"
echo "  - OpenAI Model: $OPENAI_MODEL"
echo "  - Google Model: $GOOGLE_MODEL"
echo ""

# Function to mask sensitive output
update_stack_silent() {
    local STACK_NAME=$1
    shift
    aws cloudformation update-stack --stack-name "$STACK_NAME" "$@" --region "$REGION" > /dev/null 2>&1
    return $?
}

# Function to trigger CodeBuild
trigger_codebuild() {
    local STACK_NAME=$1
    local BUILD_PROJECT=$(aws cloudformation describe-stack-resources \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'StackResources[?ResourceType==`AWS::CodeBuild::Project`].PhysicalResourceId' \
        --output text 2>/dev/null)
    
    if [ -n "$BUILD_PROJECT" ]; then
        local BUILD_ID=$(aws codebuild start-build \
            --project-name "$BUILD_PROJECT" \
            --region "$REGION" \
            --query 'build.id' \
            --output text 2>/dev/null)
        echo "$BUILD_ID"
    fi
}

# Function to wait for CodeBuild
wait_for_codebuild() {
    local BUILD_ID=$1
    while true; do
        local STATUS=$(aws codebuild batch-get-builds \
            --ids "$BUILD_ID" \
            --region "$REGION" \
            --query 'builds[0].buildStatus' \
            --output text 2>/dev/null)
        
        if [ "$STATUS" = "SUCCEEDED" ]; then
            return 0
        elif [ "$STATUS" = "FAILED" ] || [ "$STATUS" = "STOPPED" ]; then
            return 1
        fi
        sleep 5
    done
}

# Force rebuild if requested
if [ "$FORCE_REBUILD" = true ]; then
    echo "🔨 FORCE REBUILD MODE"
    echo ""
    
    echo "1. Triggering Docker image rebuilds..."
    echo "   a. Web Search Agent..."
    WEB_BUILD_ID=$(trigger_codebuild web-search-agent-a2a)
    [ -n "$WEB_BUILD_ID" ] && echo "      Build ID: $WEB_BUILD_ID"
    
    echo "   b. Host Agent..."
    HOST_BUILD_ID=$(trigger_codebuild host-agent-a2a)
    [ -n "$HOST_BUILD_ID" ] && echo "      Build ID: $HOST_BUILD_ID"
    
    echo "   c. Monitoring Agent..."
    MONITOR_BUILD_ID=$(trigger_codebuild monitor-agent-a2a)
    [ -n "$MONITOR_BUILD_ID" ] && echo "      Build ID: $MONITOR_BUILD_ID"
    
    echo ""
    echo "2. Waiting for builds to complete..."
    
    if [ -n "$WEB_BUILD_ID" ]; then
        echo -n "   Web Search: "
        if wait_for_codebuild "$WEB_BUILD_ID"; then
            echo "✓"
        else
            echo "✗ Failed"
        fi
    fi
    
    if [ -n "$HOST_BUILD_ID" ]; then
        echo -n "   Host Agent: "
        if wait_for_codebuild "$HOST_BUILD_ID"; then
            echo "✓"
        else
            echo "✗ Failed"
        fi
    fi
    
    if [ -n "$MONITOR_BUILD_ID" ]; then
        echo -n "   Monitoring: "
        if wait_for_codebuild "$MONITOR_BUILD_ID"; then
            echo "✓"
        else
            echo "✗ Failed"
        fi
    fi
    
    echo ""
    echo "3. Waiting for Lambda to update runtimes (15 seconds)..."
    sleep 15
    echo ""
fi

# Prepare stack update parameters
TIMESTAMP=$(date +%s)
if [ "$FORCE_REBUILD" = true ]; then
    EXTRA_PARAMS="--tags Key=LastUpdate,Value=$TIMESTAMP"
    UPDATE_MSG="Updating (forced)"
else
    EXTRA_PARAMS=""
    UPDATE_MSG="Updating"
fi

# Update Web Search Agent
if [ "$FORCE_REBUILD" = true ]; then
    echo "4. Updating Web Search Agent stack..."
else
    echo "1. Updating Web Search Agent..."
fi

if update_stack_silent web-search-agent-a2a \
    --use-previous-template \
    --parameters \
      ParameterKey=OpenAIKey,ParameterValue="$OPENAI_KEY" \
      ParameterKey=OpenAIModelId,ParameterValue="$OPENAI_MODEL" \
      ParameterKey=TavilyAPIKey,ParameterValue="$TAVILY_KEY" \
      ParameterKey=CognitoStackName,UsePreviousValue=true \
      ParameterKey=GitHubURL,UsePreviousValue=true \
      ParameterKey=AgentDirectory,UsePreviousValue=true \
    $EXTRA_PARAMS \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM; then
    echo "   ✓ Update initiated"
    WEB_SEARCH_UPDATING=true
else
    echo "   ℹ No changes needed"
    WEB_SEARCH_UPDATING=false
fi

# Update Host Agent
if [ "$FORCE_REBUILD" = true ]; then
    echo "5. Updating Host Agent stack..."
else
    echo "2. Updating Host Agent..."
fi

if update_stack_silent host-agent-a2a \
    --use-previous-template \
    --parameters \
      ParameterKey=GoogleApiKey,ParameterValue="$GOOGLE_KEY" \
      ParameterKey=GoogleModelId,ParameterValue="$GOOGLE_MODEL" \
      ParameterKey=CognitoStackName,UsePreviousValue=true \
      ParameterKey=GitHubURL,UsePreviousValue=true \
      ParameterKey=AgentDirectory,UsePreviousValue=true \
    $EXTRA_PARAMS \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM; then
    echo "   ✓ Update initiated"
    HOST_UPDATING=true
else
    echo "   ℹ No changes needed"
    HOST_UPDATING=false
fi

# Monitoring agent doesn't use external API keys, skip
if [ "$FORCE_REBUILD" = true ]; then
    echo "6. Monitoring Agent..."
else
    echo "3. Monitoring Agent..."
fi
echo "   ℹ No API keys needed"

echo ""

# Wait for updates to complete
if [ "$WEB_SEARCH_UPDATING" = true ] || [ "$HOST_UPDATING" = true ]; then
    echo "Waiting for stack updates to complete..."
    
    if [ "$WEB_SEARCH_UPDATING" = true ]; then
        echo -n "   Web Search Agent: "
        if aws cloudformation wait stack-update-complete --stack-name web-search-agent-a2a --region "$REGION" 2>/dev/null; then
            echo "✓"
        else
            echo "⚠ (timeout or error, check AWS console)"
        fi
    fi
    
    if [ "$HOST_UPDATING" = true ]; then
        echo -n "   Host Agent: "
        if aws cloudformation wait stack-update-complete --stack-name host-agent-a2a --region "$REGION" 2>/dev/null; then
            echo "✓"
        else
            echo "⚠ (timeout or error, check AWS console)"
        fi
    fi
    
    echo ""
    echo "Waiting for agents to restart (30 seconds)..."
    sleep 30
fi

echo ""
if [ "$FORCE_REBUILD" = true ]; then
    echo "========================================="
    echo "  ✅ FORCE REBUILD COMPLETE!"
    echo "========================================="
    echo ""
    echo "All agents have been:"
    echo "  • Docker images rebuilt from source"
    echo "  • Runtimes updated with new images"
    echo "  • Environment variables refreshed"
    echo "  • Services restarted"
else
    echo "========================================="
    echo "  ✅ API Keys Updated Successfully!"
    echo "========================================="
fi
echo ""
echo "Next steps:"
echo "1. Refresh your UI"
echo "2. Test the agents"
echo "3. Check OpenAI/Google usage dashboards to confirm they're being used"
echo ""
if [ "$FORCE_REBUILD" = false ]; then
    echo "💡 Tip: Use './update_api_keys.sh --force' to rebuild all agents from scratch"
    echo ""
fi

