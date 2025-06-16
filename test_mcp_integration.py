#!/usr/bin/env python3
"""
Test script for MCP integration with AWS DataZone server.
"""

import asyncio
import os
from dotenv import load_dotenv
from src.smus_admin_agent import SMUSAdminAgent

# Load environment variables
load_dotenv()

async def test_mcp_integration():
    """Test the MCP integration with DataZone server."""
    
    print("🔍 Debug: Checking environment variables...")
    print(f"MCP_SERVER_PATH: {os.getenv('MCP_SERVER_PATH')}")
    print(f"ANTHROPIC_API_KEY: {'Set' if os.getenv('ANTHROPIC_API_KEY') else 'Not set'}")
    
    # Create the agent
    print("🔍 Debug: Creating agent...")
    agent = SMUSAdminAgent()
    
    print(f"🔍 Debug: Agent MCP client: {agent.mcp_client}")
    print(f"🔍 Debug: Config MCP configured: {agent.config.is_mcp_configured}")
    print(f"🔍 Debug: Has server params: {hasattr(agent, 'server_params')}")
    
    # Try to ensure MCP client is connected
    print("🔍 Debug: Attempting to connect MCP client...")
    mcp_available = await agent._ensure_mcp_client()
    
    if not mcp_available:
        print("❌ MCP client could not be connected. Please check your configuration.")
        print("Make sure you have set MCP_SERVER_PATH in your .env file.")
        print("Also ensure the DataZone MCP server is properly installed.")
        return
    
    print("✅ MCP client connected successfully!")
    
    try:
        # List available tools
        print("\n📋 Listing available MCP tools...")
        tools = await agent.list_mcp_tools()
        if tools:
            print(f"Found {len(tools)} tools:")
            for tool in tools:
                print(f"  - {tool}")
        else:
            print("No tools found or failed to list tools.")
            return
        
        # Example: Call a DataZone tool (you'll need to adjust based on available tools)
        print("\n🔧 Testing tool call...")
        
        # This is just an example - you'll need to use actual tool names and parameters
        # from your DataZone MCP server
        if "list_domains" in tools:
            print("Calling list_domains...")
            result = await agent.call_mcp_tool("list_domains", {})
            print(f"Result: {result}")
        elif "get_domain" in tools:
            print("Calling get_domain (you may need to provide a valid domain_identifier)...")
            # You'll need to replace with a valid domain identifier
            # result = await agent.call_mcp_tool("get_domain", {"identifier": "your_domain_id"})
            print("Skipping get_domain call - requires valid domain identifier")
        else:
            print("No suitable test tools found. Available tools:", tools)
    
    except Exception as e:
        print(f"❌ Error during MCP testing: {e}")
    
    finally:
        # Clean up MCP resources
        await agent.cleanup_mcp()

async def test_agent_with_mcp():
    """Test the agent's streaming response with potential MCP integration."""
    
    agent = SMUSAdminAgent()
    
    print("\n🤖 Testing agent response...")
    
    # Test a simple query
    query = "Hello, can you help me understand AWS DataZone?"
    
    print(f"Query: {query}")
    print("Response: ", end="", flush=True)
    
    async for chunk in agent.stream_response(query):
        print(chunk, end="", flush=True)
    
    print("\n")

if __name__ == "__main__":
    print("🚀 Starting MCP Integration Test")
    print("=" * 50)
    
    # Check environment variables
    mcp_path = os.getenv("MCP_SERVER_PATH")
    if not mcp_path:
        print("⚠️  MCP_SERVER_PATH not set in environment variables.")
        print("Please create a .env file with:")
        print("MCP_SERVER_PATH=/Volumes/workplace/amazon-datazone-mcp-server")
        exit(1)
    
    print(f"MCP Server Path: {mcp_path}")
    
    # Run the tests
    asyncio.run(test_mcp_integration())
    asyncio.run(test_agent_with_mcp())
    
    print("\n✅ Test completed!") 