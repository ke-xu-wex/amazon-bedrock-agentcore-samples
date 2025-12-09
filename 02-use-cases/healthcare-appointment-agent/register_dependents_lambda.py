#!/usr/bin/env python3
"""
Register Lambda with CORRECT MCP tool schema (not OpenAPI)
"""
import boto3
import time

session = boto3.Session(profile_name='ai-dev', region_name='us-east-1')
client = session.client('bedrock-agentcore-control')

GATEWAY_ID = "healthcare-fhir-gateway-fqssvsgzsg"
LAMBDA_ARN = "arn:aws:lambda:us-east-1:975049916663:function:dependents-api-proxy"

# MCP tool schema format (list of tools with inputSchema)
tools = [
    {
        "name": "list_persons",
        "description": "List all persons (primary users or dependents) with optional filtering by type, status, or primary user ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "description": "Use 'list_persons' for this tool"},
                "limit": {"type": "integer", "description": "Max results to return (default 10)"},
                "offset": {"type": "integer", "description": "Pagination offset (default 0)"},
                "type": {"type": "string", "description": "Filter by type: primary or dependent"},
                "primary_user_id": {"type": "string", "description": "Filter dependents of this user"},
                "status": {"type": "string", "description": "Filter by status: active or inactive"}
            },
            "required": ["action_type"]
        }
    },
    {
        "name": "create_person",
        "description": "Create a new person (primary user or dependent) in the system",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "description": "Use 'create_person' for this tool"},
                "external_id": {"type": "string"},
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "date_of_birth": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "address": {"type": "string"},
                "type": {"type": "string", "description": "Person type: primary or dependent"}
            },
            "required": ["action_type", "external_id", "first_name", "last_name", "date_of_birth", "email"]
        }
    },
    {
        "name": "get_person",
        "description": "Get detailed information about a specific person by their ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "description": "Use 'get_person' for this tool"},
                "person_id": {"type": "string", "description": "The ID of the person to retrieve"}
            },
            "required": ["action_type", "person_id"]
        }
    },
    {
        "name": "update_person",
        "description": "Update information for an existing person",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "description": "Use 'update_person' for this tool"},
                "person_id": {"type": "string"},
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "date_of_birth": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "address": {"type": "string"},
                "status": {"type": "string"}
            },
            "required": ["action_type", "person_id"]
        }
    },
    {
        "name": "delete_person",
        "description": "Delete a person from the system by their ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "description": "Use 'delete_person' for this tool"},
                "person_id": {"type": "string", "description": "The ID of the person to delete"}
            },
            "required": ["action_type", "person_id"]
        }
    },
    {
        "name": "list_dependents",
        "description": "List all dependents for a specific primary user",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "description": "Use 'list_dependents' for this tool"},
                "primary_user_id": {"type": "string", "description": "The primary user's ID"},
                "limit": {"type": "integer"},
                "offset": {"type": "integer"}
            },
            "required": ["action_type", "primary_user_id"]
        }
    },
    {
        "name": "create_dependent",
        "description": "Create a dependent relationship for a primary user",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "description": "Use 'create_dependent' for this tool"},
                "primary_user_id": {"type": "string"},
                "external_id": {"type": "string"},
                "first_name": {"type": "string"},
                "last_name": {"type": "string"},
                "date_of_birth": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "address": {"type": "string"},
                "relationship": {"type": "string", "description": "Relationship: spouse, child, or domestic_partner"}
            },
            "required": ["action_type", "primary_user_id", "external_id", "first_name", "last_name", "date_of_birth", "email", "relationship"]
        }
    },
    {
        "name": "delete_dependent",
        "description": "Remove a dependent relationship from a primary user",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string", "description": "Use 'delete_dependent' for this tool"},
                "primary_user_id": {"type": "string"},
                "dependent_id": {"type": "string"}
            },
            "required": ["action_type", "primary_user_id", "dependent_id"]
        }
    }
]

print("="*80)
print("Registering Lambda with CORRECT MCP tool schema")
print("="*80)
print(f"Gateway: {GATEWAY_ID}")
print(f"Lambda: {LAMBDA_ARN}")
print(f"Tools: {len(tools)}\n")

try:
    response = client.create_gateway_target(
        gatewayIdentifier=GATEWAY_ID,
        name="dependents-api-lambda-proxy",
        description="Lambda proxy for dependents-api - MCP tools with action_type",
        targetConfiguration={
            "mcp": {
                "lambda": {
                    "lambdaArn": LAMBDA_ARN,
                    "toolSchema": {
                        "inlinePayload": tools  # List of tools, not OpenAPI
                    }
                }
            }
        },
        credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}]
    )
    
    print(f"✓ Created! Target ID: {response['targetId']}")
    target_id = response['targetId']
    
    # Wait for READY
    print("\nWaiting for READY status...")
    for i in range(30):
        r = client.get_gateway_target(gatewayIdentifier=GATEWAY_ID, targetIdentifier=target_id)
        status = r['status']
        print(f"  [{i+1}] {status}")
        if status == 'READY':
            print("\n✓✓✓ TARGET IS READY! ✓✓✓\n")
            break
        elif status == 'FAILED':
            print(f"\n✗ FAILED: {r.get('failureReason')}\n")
            break
        time.sleep(5)
    
    print("="*80)
    print("TEST NOW:")
    print("  python langgraph_agent_gemini.py --gateway_id healthcare-fhir-gateway-fqssvsgzsg")
    print("  Query: 'List all people'")
    print("="*80)

except Exception as e:
    print(f"\n✗ Error: {e}")

