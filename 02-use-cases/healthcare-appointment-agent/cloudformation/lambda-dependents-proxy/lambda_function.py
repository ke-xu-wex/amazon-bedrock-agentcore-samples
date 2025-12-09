"""
Lambda proxy for dependents-api in EKS
Handles all 8 dependents-api operations via internal NLB
"""
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
import logging
import os
import urllib3
import ssl

# Disable SSL warnings for internal NLB communication
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Internal NLB endpoint for dependents-api
NLB_ENDPOINT = os.getenv(
    'NLB_ENDPOINT',
    'http://tf-lb-20250808165539218800000018-b8275711ad86860d.elb.us-east-1.amazonaws.com'
)

# Create a custom SSL context that accepts any certificate
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

# Create a session with custom SSL adapter
session = requests.Session()
session.mount('https://', SSLAdapter())

def lambda_handler(event, context):
    """
    Main Lambda handler for all dependents-api operations
    
    Gateway sends:
    - event: The tool arguments directly (no wrapper)
    - context.client_context.custom['bedrockAgentCoreToolName']: The tool name
    """
    logger.info(f"Received event: {json.dumps(event)}")
    logger.info(f"Context: {context.client_context}")
    
    # Get tool name from Lambda context (Gateway standard)
    tool_name = context.client_context.custom.get('bedrockAgentCoreToolName', '')
    
    # Strip target prefix if present (e.g., "dependents-api-lambda-proxy___list_persons" -> "list_persons")
    delimiter = "___"
    if delimiter in tool_name:
        tool_name = tool_name[tool_name.index(delimiter) + len(delimiter):]
    
    logger.info(f"Tool name: {tool_name}")
    
    if not tool_name:
        logger.error("Missing tool name in context")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing tool name in context'})
        }
    
    # Route to appropriate handler
    handlers = {
        'create_person': handle_create_person,
        'list_persons': handle_list_persons,
        'get_person': handle_get_person,
        'update_person': handle_update_person,
        'delete_person': handle_delete_person,
        'list_dependents': handle_list_dependents,
        'create_dependent': handle_create_dependent,
        'delete_dependent': handle_delete_dependent
    }
    
    handler = handlers.get(tool_name)
    if not handler:
        logger.error(f"Unknown tool: {tool_name}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Unknown tool: {tool_name}'})
        }
    
    try:
        # Pass event directly (contains all tool arguments)
        result = handler(event)
        logger.info(f"Tool {tool_name} completed successfully")
        return result
    except Exception as e:
        logger.error(f"Error in {action_type}: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_create_person(args):
    """Create a new person (primary user or dependent)"""
    logger.info(f"Creating person with args: {args}")
    
    payload = {
        'externalId': args.get('external_id'),
        'firstName': args.get('first_name'),
        'lastName': args.get('last_name'),
        'dateOfBirth': args.get('date_of_birth'),
        'email': args.get('email'),
        'phone': args.get('phone'),
        'address': args.get('address'),
        'type': args.get('type', 'primary')
    }
    
    headers = {'Host': 'dependents-api.v2.ue1.wexapps.com'}
    
    response = session.post(
        f"{NLB_ENDPOINT}/people",
        json=payload,
        headers=headers,
        timeout=10,
        allow_redirects=True
    )
    response.raise_for_status()
    
    return {
        'statusCode': response.status_code,
        'body': json.dumps(response.json())
    }


def handle_list_persons(args):
    """List all persons with optional filtering"""
    logger.info(f"Listing persons with args: {args}")
    
    params = {
        'limit': args.get('limit', 100),
        'offset': args.get('offset', 0)
    }
    
    if args.get('type'):
        params['type'] = args.get('type')
    
    headers = {'Host': 'dependents-api.v2.ue1.wexapps.com'}
    
    response = session.get(
        f"{NLB_ENDPOINT}/people",
        params=params,
        headers=headers,
        timeout=10
    )
    
    logger.info(f"Response status: {response.status_code}, headers: {dict(response.headers)}")
    
    # Handle redirects - Istio is returning 301/302
    if response.status_code in [301, 302, 307, 308]:
        logger.warning(f"Received redirect to: {response.headers.get('Location')}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f"API returned redirect ({response.status_code}) - check Istio configuration",
                'location': response.headers.get('Location')
            })
        }
    
    response.raise_for_status()
    
    # Parse JSON response
    try:
        response_data = response.json()
    except ValueError as e:
        logger.error(f"Failed to parse JSON response: {response.text[:200]}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Invalid JSON response: {str(e)}', 'response_text': response.text[:200]})
        }
    
    return {
        'statusCode': response.status_code,
        'body': json.dumps(response_data)
    }


def handle_get_person(args):
    """Get details of a specific person by ID"""
    logger.info(f"Getting person with args: {args}")
    
    person_id = args.get('person_id')
    if not person_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'person_id is required'})
        }
    
    headers = {'Host': 'dependents-api.v2.ue1.wexapps.com'}
    
    response = session.get(
        f"{NLB_ENDPOINT}/people/{person_id}",
        headers=headers,
        timeout=10,
        allow_redirects=True
    )
    response.raise_for_status()
    
    return {
        'statusCode': response.status_code,
        'body': json.dumps(response.json())
    }


def handle_update_person(args):
    """Update an existing person's information"""
    logger.info(f"Updating person with args: {args}")
    
    person_id = args.get('person_id')
    if not person_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'person_id is required'})
        }
    
    # Build update payload with only provided fields
    payload = {}
    if args.get('first_name'):
        payload['firstName'] = args.get('first_name')
    if args.get('last_name'):
        payload['lastName'] = args.get('last_name')
    if args.get('email'):
        payload['email'] = args.get('email')
    if args.get('phone'):
        payload['phone'] = args.get('phone')
    if args.get('address'):
        payload['address'] = args.get('address')
    
    headers = {'Host': 'dependents-api.v2.ue1.wexapps.com'}
    
    response = session.patch(
        f"{NLB_ENDPOINT}/people/{person_id}",
        json=payload,
        headers=headers,
        timeout=10,
        allow_redirects=True
    )
    response.raise_for_status()
    
    return {
        'statusCode': response.status_code,
        'body': json.dumps(response.json())
    }


def handle_delete_person(args):
    """Delete a person from the system"""
    logger.info(f"Deleting person with args: {args}")
    
    person_id = args.get('person_id')
    if not person_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'person_id is required'})
        }
    
    headers = {'Host': 'dependents-api.v2.ue1.wexapps.com'}
    
    response = session.delete(
        f"{NLB_ENDPOINT}/people/{person_id}",
        headers=headers,
        timeout=10,
        allow_redirects=True
    )
    response.raise_for_status()
    
    return {
        'statusCode': response.status_code,
        'body': json.dumps({'status': 'deleted', 'person_id': person_id})
    }


def handle_list_dependents(args):
    """List all dependents for a specific primary user"""
    logger.info(f"Listing dependents with args: {args}")
    
    primary_user_id = args.get('primary_user_id')
    if not primary_user_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'primary_user_id is required'})
        }
    
    headers = {'Host': 'dependents-api.v2.ue1.wexapps.com'}
    
    response = session.get(
        f"{NLB_ENDPOINT}/people/{primary_user_id}/dependents",
        headers=headers,
        timeout=10,
        allow_redirects=True
    )
    response.raise_for_status()
    
    return {
        'statusCode': response.status_code,
        'body': json.dumps(response.json())
    }


def handle_create_dependent(args):
    """Create a relationship between a primary user and dependent"""
    logger.info(f"Creating dependent relationship with args: {args}")
    
    primary_user_id = args.get('primary_user_id')
    dependent_id = args.get('dependent_id')
    
    if not primary_user_id or not dependent_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'primary_user_id and dependent_id are required'})
        }
    
    payload = {'dependentId': dependent_id}
    headers = {'Host': 'dependents-api.v2.ue1.wexapps.com'}
    
    response = session.post(
        f"{NLB_ENDPOINT}/people/{primary_user_id}/dependents",
        json=payload,
        headers=headers,
        timeout=10,
        allow_redirects=True
    )
    response.raise_for_status()
    
    return {
        'statusCode': response.status_code,
        'body': json.dumps(response.json())
    }


def handle_delete_dependent(args):
    """Remove the relationship between a primary user and dependent"""
    logger.info(f"Deleting dependent relationship with args: {args}")
    
    primary_user_id = args.get('primary_user_id')
    dependent_id = args.get('dependent_id')
    
    if not primary_user_id or not dependent_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'primary_user_id and dependent_id are required'})
        }
    
    headers = {'Host': 'dependents-api.v2.ue1.wexapps.com'}
    
    response = session.delete(
        f"{NLB_ENDPOINT}/people/{primary_user_id}/dependents/{dependent_id}",
        headers=headers,
        timeout=10,
        allow_redirects=True
    )
    response.raise_for_status()
    
    return {
        'statusCode': response.status_code,
        'body': json.dumps({
            'status': 'relationship_deleted',
            'primary_user_id': primary_user_id,
            'dependent_id': dependent_id
        })
    }

