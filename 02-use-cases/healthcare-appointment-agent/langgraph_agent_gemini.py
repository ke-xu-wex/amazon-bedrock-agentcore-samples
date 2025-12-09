from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
import asyncio
from dotenv import load_dotenv
import argparse
import os
import sys
import utils

# Get repo root directory (2 levels up from current file)
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

# Load from both .env files
load_dotenv()  # Load local .env
load_dotenv(os.path.join(repo_root, '.env.api-key'))  # Load repo root .env.api-key

# Check for Google API key
if not os.getenv("GOOGLE_API_KEY"):
    print("❌ Error: GOOGLE_API_KEY environment variable not set")
    print("Please add it to your .env.api-key file:")
    print("  echo 'GOOGLE_API_KEY=your-api-key-here' >> .env.api-key")
    exit(1)

#setting parameters
parser = argparse.ArgumentParser(
                    prog='langgraph_agent_gemini',
                    description='Test LangGraph Agent with MCP Gateway using Gemini',
                    epilog='Input Parameters')

parser.add_argument('--gateway_id', help = "Gateway Id")
parser.add_argument('--query', help = "Single query to test (skips interactive mode)", default=None)

#create boto3 session and client
(boto_session, agentcore_client) = utils.create_agentcore_client()

async def main(gateway_endpoint, jwt_token, single_query=None):
    client = MultiServerMCPClient(
        {
            "healthcare": {
                "url": gateway_endpoint,
                "transport": "streamable_http",
                "headers":{"Authorization": f"Bearer {jwt_token}"}
            }
        }
    )

    mcp_tools = await client.get_tools()
    
    # Add direct HTTP tools for dependents-api (bypasses Gateway)
    tools = mcp_tools
    
    print(f"✓ Found {len(mcp_tools)} tools from MCP Gateway (healthcare)")
    # All tools now come from MCP Gateway (including dependents-api via Lambda proxy)
    print(f"✓ Total tools available: {len(tools)}")

    # Use Google Gemini instead of Bedrock
    LLM = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.7,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    print(f"✓ Using Google Gemini 2.5 Flash (bypasses AWS SCP restrictions)")

    systemPrompt = """
    You are a comprehensive healthcare and benefits assistant with access to:
    
    1. Healthcare Management:
       - Check immunization records for patients
       - Book medical appointments
       - View available appointment slots
       - Patient: adult-patient-001 is logged in
       - Child patient: pediatric-patient-001
    
    2. Benefits Dependents Management:
       - Create and manage primary users (employees)
       - Add and manage dependents (spouses, children)
       - List dependents for employees
       - View person details
    
    Always be helpful and address users by name. Never expose internal IDs in responses.
    When discussing immunizations, check for pending vaccinations and offer to book appointments.
    """

    agent = create_react_agent(
        LLM, 
        tools, 
        prompt=systemPrompt
    )
    
    # Initialize conversation state
    conversation_state = {"messages": []}

    # Single query mode (for automated testing)
    if single_query:
        print("\n" + "=" * 70)
        print(f"👤 Query: {single_query}")
        print("=" * 70)
        print()
        
        conversation_state["messages"].append(("human", single_query))
        
        print("🤖 Healthcarebot: ", end="")
        response_text = ""
        async for chunk in agent.astream(conversation_state, stream_mode="values"):
            if messages := chunk.get("messages"):
                last_msg = messages[-1]
                if hasattr(last_msg, 'type') and last_msg.type == "ai":
                    if hasattr(last_msg, 'content') and last_msg.content:
                        if last_msg.content != response_text:
                            new_text = last_msg.content[len(response_text):]
                            print(new_text, end="", flush=True)
                            response_text = last_msg.content
        
        print("\n")
        print("=" * 70)
        print("✅ Test completed successfully!")
        print("=" * 70)
        return

    print("=" * 70)
    print("🏥  HEALTHCARE & BENEFITS ASSISTANT  🏥")
    print("=" * 70)
    print("✨ I can help you with:")
    print()
    print("   Healthcare Services:")
    print("   📅 Check immunization history and pending vaccinations")
    print("   📋 Book medical appointments")
    print("   🕐 View available appointment slots")
    print()
    print("   Benefits Management:")
    print("   👥 Create and manage primary users (employees)")
    print("   👨‍👩‍👧‍👦 Add and manage dependents (spouses, children)")
    print("   📝 List dependents for employees")
    print()
    print("🤖 Powered by: Google Gemini 2.5 Flash")
    print("🔧 MCP Gateway: AgentCore (All 12 tools enabled)")
    print("🚪 Type 'exit' to quit anytime")
    print("=" * 70)
    print()

    # Run the agent in a loop for interactive conversation
    while True:
        try:
            user_input = input("👤 You: ").strip()

            if not user_input:
                print("💭 Please enter a message or type 'exit' to quit")
                continue

            if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
                print()
                print("=======================================")
                print("👋 Thanks for using Healthcare Assistant!")
                print("🎉 Have a great day ahead!")
                print("=======================================")
                break

            print("🤖 Healthcarebot: ", end="")

            # Add user message to conversation state
            conversation_state["messages"].append(("human", user_input))
            
            # Stream the response
            response_text = ""
            async for chunk in agent.astream(conversation_state, stream_mode="values"):
                if messages := chunk.get("messages"):
                    # Get the last AI message
                    last_msg = messages[-1]
                    if hasattr(last_msg, 'type') and last_msg.type == "ai":
                        if hasattr(last_msg, 'content') and last_msg.content:
                            # Only print new content
                            if last_msg.content != response_text:
                                new_text = last_msg.content[len(response_text):]
                                print(new_text, end="", flush=True)
                                response_text = last_msg.content
            
            # Update conversation state with the response
            conversation_state = chunk

            print()

        except KeyboardInterrupt:
            print()
            print("=======================================")
            print("👋 Healthcare Assistant interrupted!")
            print("🎉 See you next time!")
            print("=======================================")
            break
        except Exception as e:
            print(f"❌ An error occurred: {str(e)}")
            print("💡 Please try again or type 'exit' to quit")
            print()

if __name__ == "__main__":
    args = parser.parse_args()

    #Validations
    if args.gateway_id is None:
        raise Exception("Gateway Id is required")

    gatewayEndpoint=utils.get_gateway_endpoint(agentcore_client=agentcore_client, gateway_id=args.gateway_id)
    print(f"Gateway Endpoint: {gatewayEndpoint}")

    jwtToken = utils.get_oath_token(boto_session)
    asyncio.run(main(gatewayEndpoint, jwtToken, single_query=args.query))

